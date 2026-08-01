#!/usr/bin/env python3
"""In-play win-probability model for the mini-TRADE360 pipeline.

Pure stdlib, importable standalone. The model is still one formula per team
- expected goals still to come - but v3 corrects three things the v2 fit got
wrong, each of them measured on a held-out season rather than assumed:

    lam_rem(t) = rem(t) * ((1 - w) * lam_prematch + w * 90 * pace) * adj

  rem(t)  share of a match's goal-scoring still ahead at minute t. v2 used
          the straight line (90 - t) / 90; v3 uses the EMPIRICAL profile
          measured from the training corpus, because goals are not spread
          evenly - the last twenty minutes carry more xG than the first.
  pace    xG created in the last `window` minutes / window, i.e. the team's
          current scoring rate per minute (the live-momentum term).
  w       momentum weight. v2 shipped 0.35; the holdout says 0.05. Fifteen
          minutes of xG is a noisy estimate of anything, and most of what it
          seems to measure is really score state (below).
  adj     multiplicative adjustments for the things a bare Poisson misses:
          SCORE STATE (a trailing team pushes, a leading team defends) and
          RED CARDS (a team down to ten scores less, concedes more).

The remaining-goals counts are Poisson, so with the current score (h, a):

    P(home win) = sum over i,j  Pois(i; lam_rem_h) * Pois(j; lam_rem_a)
                                * tau(i, j) * [h+i > a+j]

Draw and away are the analogous [==] and [<] sums. tau is the Dixon-Coles
low-score correction, which reweights the four cells where both sides score
at most once - independent Poissons get that corner slightly wrong, and the
SIGN of rho decides which way. Fitting it on held-out football picked a
small POSITIVE rho: marginally fewer 0-0 and 1-1 results, and more 1-0 and
0-1, than independence implies. That is the same message as the draw
experiments, which found this model does not need its draws inflated. A
small effect, but free.

All the shape parameters (profile, w, rho, score-state and red-card
multipliers) are FIT, not chosen: see calibrate.py, which tunes them on a
validation season the holdout never sees.
"""
import math

MAX_GOALS = 10          # truncation of the Poisson grid; tail mass renormalized
DEFAULT_W = 0.05        # weight of live momentum vs pre-match expectation
DEFAULT_WINDOW = 15     # minutes of xG history that define "current pace"
LAM_FLOOR = 0.05        # a team is never fully dead: >= 0.05 xG per full match
ODDS_CAP = 999.0        # fair odds cap for near-impossible outcomes

# Dixon-Coles low-score dependence. rho > 0 damps the low-score DRAWS
# (0-0, 1-1) and lifts the one-goal wins; rho < 0 is the reverse.
DEFAULT_RHO = 0.0
# Score-state adjustment, as log multipliers on remaining lambda: a leading
# team's rate is scaled by exp(b_lead), a trailing team's by exp(b_trail).
DEFAULT_B_LEAD = 0.0
DEFAULT_B_TRAIL = 0.0
# Red-card adjustment: the dismissed side's remaining rate is scaled by
# red_self, its opponent's by red_opp.
DEFAULT_RED_SELF = 1.0
DEFAULT_RED_OPP = 1.0


def poisson_pmf(i, lam):
    """P(X = i) for X ~ Poisson(lam). Handles lam = 0 (all mass at 0)."""
    return math.exp(-lam) * lam ** i / math.factorial(i)


def effective_min(event_min, has_extra_time):
    """Minute an event counts at for the 90-minute market, or None if it
    doesn't count. In a match WITHOUT extra time (every league match, every
    World Cup group game) min > 90 is second-half stoppage and folds into
    minute 90 — a 90+4' goal settles the market. In a match WITH extra time
    (World Cup knockouts) min > 90 is extra time and never enters. The
    caller decides `has_extra_time` from the competition and stage; this
    function stays a pure truth table."""
    if event_min <= 90:
        return event_min
    if not has_extra_time:
        return 90
    return None


def remaining_fraction(t, profile=None):
    """Share of a match's total goal-scoring still ahead at minute t.

    With no profile this is the straight line (90 - t) / 90 — the v2
    behaviour, and what you get if you assume goals arrive at a constant
    rate. With a profile (91 floats, profile[m] = share of corpus xG struck
    after minute m, so profile[0] = 1.0 and profile[90] = 0.0) it is the
    measured shape instead; fractional minutes interpolate linearly, which
    matters because the dashboards sample just before a goal minute to keep
    the jump sharp."""
    if t >= 90.0:
        return 0.0
    if t < 0.0:
        t = 0.0
    if not profile:
        return (90.0 - t) / 90.0
    i = int(t)
    lo = profile[i]
    hi = profile[i + 1] if i + 1 < len(profile) else 0.0
    return lo + (hi - lo) * (t - i)


def dc_tau(i, j, lam_h, lam_a, rho):
    """Dixon-Coles correction for the four low-score cells.

    Independent Poissons misprice the corner where both sides score at most
    once. tau reweights exactly those four cells and leaves every other
    score alone, so it is a two-goal-neighbourhood patch rather than a new
    model. With rho > 0 the low-score DRAWS (0-0, 1-1) are damped and the
    one-goal wins lifted; rho < 0 does the reverse, which is the classic
    Dixon-Coles direction for full-match league scores. This model's fit
    chose rho > 0. Clamped at 0 so a large rho can never produce a negative
    probability."""
    if not rho or i > 1 or j > 1:
        return 1.0
    if i == 0 and j == 0:
        return max(0.0, 1.0 - lam_h * lam_a * rho)
    if i == 0 and j == 1:
        return max(0.0, 1.0 + lam_h * rho)
    if i == 1 and j == 0:
        return max(0.0, 1.0 + lam_a * rho)
    return max(0.0, 1.0 - rho)


def win_probs(lam_rem_h, lam_rem_a, h, a, max_goals=MAX_GOALS, rho=DEFAULT_RHO):
    """(pH, pD, pA) given expected REMAINING goals and the current score.

    Sums an independent-Poisson grid of remaining goals (0..max_goals each
    side), applies the Dixon-Coles low-score correction, and buckets every
    cell by the final score h+i vs a+j. The triple is renormalized to sum
    exactly to 1.0 (the grid truncates the tail, and tau is not
    mass-preserving)."""
    ph = pd = pa = 0.0
    pmf_h = [poisson_pmf(i, lam_rem_h) for i in range(max_goals + 1)]
    pmf_a = [poisson_pmf(j, lam_rem_a) for j in range(max_goals + 1)]
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = pmf_h[i] * pmf_a[j] * dc_tau(i, j, lam_rem_h, lam_rem_a, rho)
            if h + i > a + j:
                ph += p
            elif h + i == a + j:
                pd += p
            else:
                pa += p
    total = ph + pd + pa
    return ph / total, pd / total, pa / total


def lam_remaining(t, lam_prematch, xg_recent, w=DEFAULT_W, floor=LAM_FLOOR,
                  window=DEFAULT_WINDOW, profile=None):
    """Expected goals a team still scores between minute t and 90.

    Blends the pre-match rate with live momentum (xG created in the last
    `window` minutes, extrapolated to a full match), then scales by the
    share of the match's scoring still ahead:

        lam_rem = rem(t) * ((1 - w) * lam_prematch + w * 90 * pace)

    with pace = xg_recent / window (xG per minute). Clamped from below at
    floor * rem(t) so a dominated team never drops to zero; at t >= 90 there
    is no time left and the answer is 0. Score-state and red-card
    multipliers are applied by the caller (InPlayModel.probs), because they
    depend on match state this function is deliberately not given."""
    frac = remaining_fraction(t, profile)
    if frac <= 0.0:
        return 0.0
    pace = xg_recent / float(window)
    lam = frac * ((1.0 - w) * lam_prematch + w * 90.0 * pace)
    return max(lam, floor * frac)


def score_state_factors(score_h, score_a, b_lead=DEFAULT_B_LEAD,
                        b_trail=DEFAULT_B_TRAIL):
    """(home factor, away factor) for the current scoreline.

    A team that is ahead protects the lead and creates less; a team that is
    behind chases and creates more. The fitted asymmetry is large — trailing
    sides get most of the adjustment — and it is the single biggest v3 gain,
    because it captures what the v2 momentum term was really picking up:
    teams do not shoot more because they are "hot", they shoot more because
    they are losing. Level scores are unadjusted by construction."""
    d = score_h - score_a
    if d == 0 or (not b_lead and not b_trail):
        return 1.0, 1.0
    lead, trail = math.exp(b_lead), math.exp(b_trail)
    return (lead, trail) if d > 0 else (trail, lead)


def red_card_factors(red_h, red_a, red_self=DEFAULT_RED_SELF,
                     red_opp=DEFAULT_RED_OPP):
    """(home factor, away factor) for red cards shown so far.

    A side reduced to ten men scores at a lower rate (`red_self`) and lets
    its opponent score at a higher one (`red_opp`); two dismissals compound.
    Rare (about one league match in eight) and usually late, so this barely
    moves an aggregate Brier score — it is here because a market that
    ignores a sending-off is wrong in exactly the situation a trader would
    notice first."""
    fh = fa = 1.0
    for _ in range(int(red_h or 0)):
        fh *= red_self
        fa *= red_opp
    for _ in range(int(red_a or 0)):
        fa *= red_self
        fh *= red_opp
    return fh, fa


def fair_odds(p):
    """Fair (no-margin) decimal odds 1/p, capped at ODDS_CAP for tiny p."""
    if p < 0.001:
        return ODDS_CAP
    return 1.0 / p


def book_prices(ph, pd, pa, overround=1.05):
    """Bookmaker-style decimal prices with a margin baked in.

    The three probabilities are scaled so their implied sum equals
    `overround` (e.g. 1.05 = a 5% margin), then inverted to prices."""
    total = ph + pd + pa
    prices = []
    for p in (ph, pd, pa):
        scaled = p * overround / total
        prices.append(ODDS_CAP if scaled < 0.001 else 1.0 / scaled)
    return tuple(prices)


class InPlayModel:
    """Live 1X2 model for one fixture.

    Per team, expected remaining goals = share of the scoring still ahead x
    a blend of what we thought before kickoff and how the team is playing
    right now, adjusted for score state and red cards:

        lam_rem(t) = rem(t) * ((1 - w) * lam_prematch + w * 90 * pace) * adj

    Feed the two lam_rem values plus the current score into a Dixon-Coles
    corrected Poisson grid to get P(home)/P(draw)/P(away), fair odds, and
    booked prices.

    Every shape parameter defaults to the neutral v2 behaviour, so an
    InPlayModel built with only (lam_h, lam_a) is the plain textbook model;
    calibrate.py supplies the fitted values via from_params()."""

    def __init__(self, lam_h, lam_a, w=DEFAULT_W, profile=None,
                 window=DEFAULT_WINDOW, rho=DEFAULT_RHO,
                 b_lead=DEFAULT_B_LEAD, b_trail=DEFAULT_B_TRAIL,
                 red_self=DEFAULT_RED_SELF, red_opp=DEFAULT_RED_OPP):
        self.lam_h = lam_h      # pre-match expected goals, home
        self.lam_a = lam_a      # pre-match expected goals, away
        self.w = w              # momentum weight
        self.profile = profile  # empirical remaining-scoring curve (or None)
        self.window = window    # momentum window, minutes
        self.rho = rho          # Dixon-Coles low-score correction
        self.b_lead = b_lead    # log multiplier applied to a leading side
        self.b_trail = b_trail  # log multiplier applied to a trailing side
        self.red_self = red_self
        self.red_opp = red_opp

    @classmethod
    def from_params(cls, lam_h, lam_a, params):
        """Build from a model_params.json dict (v2 or v3). Missing keys keep
        their neutral defaults, so a v2 params file still loads and prices
        exactly as it used to."""
        red = params.get("red") or {}
        return cls(
            lam_h, lam_a,
            w=params.get("w", DEFAULT_W),
            profile=params.get("profile"),
            window=params.get("window", DEFAULT_WINDOW),
            rho=params.get("rho", DEFAULT_RHO),
            b_lead=params.get("b_lead", DEFAULT_B_LEAD),
            b_trail=params.get("b_trail", DEFAULT_B_TRAIL),
            red_self=red.get("self", DEFAULT_RED_SELF),
            red_opp=red.get("opp", DEFAULT_RED_OPP),
        )

    def lams(self, t, score_h, score_a, xg_recent_h, xg_recent_a,
             red_h=0, red_a=0, horizon=None):
        """Expected remaining goals per side at minute t, fully adjusted.

        `horizon` overrides the remaining-time fraction for clocks that run
        past 90' (stoppage, extra time), where the profile — which is
        defined on the 90-minute market clock — does not apply."""
        lams = []
        for lam_pre, xg_recent in ((self.lam_h, xg_recent_h),
                                   (self.lam_a, xg_recent_a)):
            if horizon is None:
                lam = lam_remaining(t, lam_pre, xg_recent, self.w,
                                    window=self.window, profile=self.profile)
            else:
                pace = xg_recent / float(self.window)
                lam = horizon * ((1.0 - self.w) * lam_pre + self.w * 90.0 * pace)
                lam = max(lam, LAM_FLOOR * horizon)
            lams.append(lam)
        sh, sa = score_state_factors(score_h, score_a, self.b_lead, self.b_trail)
        rh, ra = red_card_factors(red_h, red_a, self.red_self, self.red_opp)
        return lams[0] * sh * rh, lams[1] * sa * ra

    def probs(self, t, score_h, score_a, xg_recent15_h, xg_recent15_a,
              red_h=0, red_a=0, horizon=None):
        """1X2 snapshot at minute t. Returns a dict with probabilities
        (pH/pD/pA), fair odds (fairH/fairD/fairA) and 5%-margin book
        prices (bookH/bookD/bookA)."""
        lam_rem_h, lam_rem_a = self.lams(t, score_h, score_a, xg_recent15_h,
                                         xg_recent15_a, red_h, red_a, horizon)
        ph, pd, pa = win_probs(lam_rem_h, lam_rem_a, score_h, score_a,
                               rho=self.rho)
        bh, bd, ba = book_prices(ph, pd, pa)
        return {
            "pH": ph, "pD": pd, "pA": pa,
            "fairH": fair_odds(ph), "fairD": fair_odds(pd), "fairA": fair_odds(pa),
            "bookH": bh, "bookD": bd, "bookA": ba,
        }
