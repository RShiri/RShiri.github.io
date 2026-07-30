#!/usr/bin/env python3
"""In-play win-probability model for the mini-TRADE360 pipeline.

Pure stdlib, importable standalone. The whole model is one teaching formula:

    lam_rem(t) = ((90 - t) / 90) * ((1 - w) * lam_prematch + w * 90 * pace)

where `pace = xG in the last 15 minutes / 15` is the team's CURRENT scoring
rate per minute, and `w` blends pre-match expectation with live momentum.
The remaining-goals counts are Poisson, so with the current score (h, a):

    P(home win) = sum over i,j  Pois(i; lam_rem_h) * Pois(j; lam_rem_a) * [h+i > a+j]

Draw and away are the analogous [==] and [<] sums.
"""
import math

MAX_GOALS = 10          # truncation of the Poisson grid; tail mass renormalized
DEFAULT_W = 0.35        # weight of live momentum vs pre-match expectation
LAM_FLOOR = 0.05        # a team is never fully dead: >= 0.05 xG per full match
ODDS_CAP = 999.0        # fair odds cap for near-impossible outcomes


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


def win_probs(lam_rem_h, lam_rem_a, h, a, max_goals=MAX_GOALS):
    """(pH, pD, pA) given expected REMAINING goals and the current score.

    Sums an independent-Poisson grid of remaining goals (0..max_goals each
    side) and buckets every cell by the final score h+i vs a+j. The triple
    is renormalized to sum exactly to 1.0 (the grid truncates the tail)."""
    ph = pd = pa = 0.0
    pmf_h = [poisson_pmf(i, lam_rem_h) for i in range(max_goals + 1)]
    pmf_a = [poisson_pmf(j, lam_rem_a) for j in range(max_goals + 1)]
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = pmf_h[i] * pmf_a[j]
            if h + i > a + j:
                ph += p
            elif h + i == a + j:
                pd += p
            else:
                pa += p
    total = ph + pd + pa
    return ph / total, pd / total, pa / total


def lam_remaining(t, lam_prematch, xg_recent15, w=DEFAULT_W, floor=LAM_FLOOR):
    """Expected goals a team still scores between minute t and 90.

    Blends the pre-match rate with live momentum (xG created in the last
    15 minutes, extrapolated to a full match), then scales by time left:

        lam_rem = ((90 - t) / 90) * ((1 - w) * lam_prematch + w * 90 * pace)

    with pace = xg_recent15 / 15 (xG per minute). Clamped from below at
    floor * (90 - t) / 90 so a dominated team never drops to zero; at
    t >= 90 there is no time left and the answer is 0."""
    if t >= 90:
        return 0.0
    frac = (90.0 - t) / 90.0
    pace = xg_recent15 / 15.0
    lam = frac * ((1.0 - w) * lam_prematch + w * 90.0 * pace)
    return max(lam, floor * frac)


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

    The one formula that drives everything (per team):

        lam_rem(t) = ((90 - t) / 90) * ((1 - w) * lam_prematch
                                        + w * 90 * (xg_recent15 / 15))

    i.e. expected remaining goals = time left x a blend of what we thought
    before kickoff and how the team is actually playing right now. Feed the
    two lam_rem values plus the current score into an independent-Poisson
    grid to get P(home)/P(draw)/P(away), fair odds, and booked prices."""

    def __init__(self, lam_h, lam_a, w=DEFAULT_W):
        self.lam_h = lam_h      # pre-match expected goals, home
        self.lam_a = lam_a      # pre-match expected goals, away
        self.w = w              # momentum weight

    def probs(self, t, score_h, score_a, xg_recent15_h, xg_recent15_a):
        """1X2 snapshot at minute t. Returns a dict with probabilities
        (pH/pD/pA), fair odds (fairH/fairD/fairA) and 5%-margin book
        prices (bookH/bookD/bookA)."""
        lam_rem_h = lam_remaining(t, self.lam_h, xg_recent15_h, self.w)
        lam_rem_a = lam_remaining(t, self.lam_a, xg_recent15_a, self.w)
        ph, pd, pa = win_probs(lam_rem_h, lam_rem_a, score_h, score_a)
        bh, bd, ba = book_prices(ph, pd, pa)
        return {
            "pH": ph, "pD": pd, "pA": pa,
            "fairH": fair_odds(ph), "fairD": fair_odds(pd), "fairA": fair_odds(pa),
            "bookH": bh, "bookD": bd, "bookA": ba,
        }
