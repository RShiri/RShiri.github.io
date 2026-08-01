"""Tests for the in-play win-probability model (tradepipe/model.py).

Run from the repo root:
    python3 -m pytest live-pipeline/tests/test_model.py -q

model.py is loaded directly by file path so the tests do not depend on the
tradepipe package (or its __init__) being importable.
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "winprob_model", HERE.parent / "tradepipe" / "model.py")
model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model)


def test_effective_min_truth_table():
    # regulation minutes pass through untouched
    assert model.effective_min(1, False) == 1
    assert model.effective_min(45, True) == 45
    assert model.effective_min(90, False) == 90
    assert model.effective_min(90, True) == 90
    # no extra time (leagues, WC group games): min > 90 is stoppage -> 90.
    # A league 90+4' goal MUST settle the 90-minute market.
    assert model.effective_min(94, False) == 90
    assert model.effective_min(92, False) == 90
    assert model.effective_min(98, False) == 90
    # extra time (WC knockouts): min > 90 never enters the 90-min market
    assert model.effective_min(94, True) is None
    assert model.effective_min(105, True) is None
    assert model.effective_min(120, True) is None


def test_probs_sum_to_one_across_state_grid():
    for lam_h, lam_a in [(0.3, 0.3), (1.5, 0.8), (2.4, 2.4), (0.05, 3.0)]:
        m = model.InPlayModel(lam_h, lam_a)
        for t in range(0, 91, 15):
            for h in range(4):
                for a in range(4):
                    p = m.probs(t, h, a, 0.4, 0.2)
                    total = p["pH"] + p["pD"] + p["pA"]
                    assert abs(total - 1.0) < 1e-9, (t, h, a, total)


def test_home_goal_raises_ph_and_lowers_pa():
    for h, a in [(0, 0), (1, 1), (0, 2), (2, 1)]:
        before = model.win_probs(0.9, 0.7, h, a)
        after = model.win_probs(0.9, 0.7, h + 1, a)
        assert after[0] > before[0]         # pH strictly up
        assert after[2] < before[2]         # pA strictly down


def test_home_lead_becomes_certain_at_full_time():
    m = model.InPlayModel(1.4, 1.1)
    # t = 90 exactly: no time left, the lead IS the outcome.
    p = m.probs(90, 1, 0, 0.0, 0.0)
    assert p["pH"] == 1.0
    assert p["pD"] == 0.0 and p["pA"] == 0.0
    # t = 89 with quiet play: near-certain but not quite.
    p89 = m.probs(89, 1, 0, 0.0, 0.0)
    assert p89["pH"] > 0.95
    assert p89["pH"] < 1.0


def test_fair_odds_and_book_prices():
    assert model.fair_odds(0.5) == 2.0
    assert model.fair_odds(0.25) == 4.0
    assert model.fair_odds(1e-6) == 999.0  # capped for near-impossible outcomes

    ph, pd, pa = 0.5, 0.3, 0.2
    bh, bd, ba = model.book_prices(ph, pd, pa, overround=1.05)
    implied = 1.0 / bh + 1.0 / bd + 1.0 / ba
    assert abs(implied - 1.05) < 1e-9
    # margin means every price is shorter than fair
    assert bh < model.fair_odds(ph)
    assert bd < model.fair_odds(pd)
    assert ba < model.fair_odds(pa)


def test_lam_remaining_time_behaviour():
    # no time left -> no goals left
    assert model.lam_remaining(90, 1.5, 0.8) == 0.0
    assert model.lam_remaining(95, 1.5, 0.8) == 0.0
    # strictly decreasing in t with pace held fixed
    vals = [model.lam_remaining(t, 1.5, 0.6) for t in range(0, 90, 5)]
    for earlier, later in zip(vals, vals[1:]):
        assert later < earlier
    # floor: a dead pre-match rate with zero momentum still leaves a pulse
    lam = model.lam_remaining(45, 0.0, 0.0, floor=0.05)
    assert abs(lam - 0.05 * 45 / 90) < 1e-12


# ---------------------------------------------------------------- v3 pieces

def test_remaining_fraction_linear_and_profile():
    # no profile -> the straight line the model used before v3
    assert model.remaining_fraction(0) == 1.0
    assert model.remaining_fraction(45) == 0.5
    assert model.remaining_fraction(90) == 0.0
    assert model.remaining_fraction(95) == 0.0
    # a profile is used verbatim at integer minutes and interpolated between
    profile = [1.0 - t / 90.0 for t in range(91)]
    assert abs(model.remaining_fraction(30, profile) - 2 / 3) < 1e-12
    assert abs(model.remaining_fraction(30.5, profile)
               - (profile[30] + profile[31]) / 2) < 1e-12
    # past the end there is nothing left regardless of the profile
    assert model.remaining_fraction(90, profile) == 0.0


def test_profile_shifts_value_from_early_to_late_minutes():
    """The fitted profile says football scores late. A model using it must
    hold MORE remaining goals at half time than the linear clock does."""
    late = [max(0.0, 1.0 - (t / 90.0) ** 2) for t in range(91)]   # back-loaded
    linear = model.lam_remaining(45, 1.4, 0.0)
    shaped = model.lam_remaining(45, 1.4, 0.0, profile=late)
    assert shaped > linear


def test_score_state_factors_direction_and_symmetry():
    # level -> untouched
    assert model.score_state_factors(1, 1, -0.05, 0.25) == (1.0, 1.0)
    # home leads: home damped, away lifted
    fh, fa = model.score_state_factors(2, 1, -0.05, 0.25)
    assert fh < 1.0 < fa
    # away leading is the mirror image
    ah, aa = model.score_state_factors(1, 2, -0.05, 0.25)
    assert (ah, aa) == (fa, fh)
    # no coefficients -> no effect
    assert model.score_state_factors(3, 0, 0.0, 0.0) == (1.0, 1.0)


def test_red_card_factors_compound_and_default_neutral():
    assert model.red_card_factors(0, 0) == (1.0, 1.0)
    fh, fa = model.red_card_factors(1, 0, red_self=0.7, red_opp=1.2)
    assert abs(fh - 0.7) < 1e-12 and abs(fa - 1.2) < 1e-12
    # two dismissals for the same side compound
    fh2, fa2 = model.red_card_factors(2, 0, red_self=0.7, red_opp=1.2)
    assert abs(fh2 - 0.49) < 1e-12 and abs(fa2 - 1.44) < 1e-12
    # one each cancels out
    fh3, fa3 = model.red_card_factors(1, 1, red_self=0.7, red_opp=1.2)
    assert abs(fh3 - fa3) < 1e-12


def test_dixon_coles_moves_only_the_low_score_cells():
    lam_h, lam_a, rho = 1.1, 0.9, 0.05
    # the four corrected cells
    assert model.dc_tau(0, 0, lam_h, lam_a, rho) != 1.0
    assert model.dc_tau(1, 1, lam_h, lam_a, rho) != 1.0
    # everything else is untouched
    for i, j in [(2, 0), (0, 2), (3, 4), (1, 2)]:
        assert model.dc_tau(i, j, lam_h, lam_a, rho) == 1.0
    # rho = 0 is the identity everywhere
    assert model.dc_tau(0, 0, lam_h, lam_a, 0.0) == 1.0


def test_rho_moves_the_draw_in_the_sign_of_rho_and_still_normalizes():
    """rho > 0 damps the low-score draws (the direction the holdout fit
    chose); rho < 0 is the classic Dixon-Coles lift. Either way the triple
    must still be a probability distribution."""
    plain = model.win_probs(1.2, 1.1, 0, 0, rho=0.0)
    damped = model.win_probs(1.2, 1.1, 0, 0, rho=0.05)
    lifted = model.win_probs(1.2, 1.1, 0, 0, rho=-0.05)
    assert damped[1] < plain[1] < lifted[1]
    for triple in (plain, damped, lifted):
        assert abs(sum(triple) - 1.0) < 1e-12
    # the correction only touches the low-score corner: with a big lead
    # already on the board it changes nothing
    assert (model.win_probs(1.2, 1.1, 4, 0, rho=0.05)
            == model.win_probs(1.2, 1.1, 4, 0, rho=0.0))


def test_from_params_defaults_to_neutral_on_a_v2_file():
    """A v2 params dict has none of the v3 keys; loading it must reproduce
    the plain model rather than crash or invent adjustments."""
    v2 = {"w": 0.35}
    m = model.InPlayModel.from_params(1.4, 1.1, v2)
    assert m.w == 0.35 and m.profile is None and m.rho == 0.0
    assert m.b_lead == 0.0 and m.b_trail == 0.0
    assert (m.red_self, m.red_opp) == (1.0, 1.0)
    plain = model.InPlayModel(1.4, 1.1, w=0.35)
    assert m.probs(30, 1, 0, 0.3, 0.2) == plain.probs(30, 1, 0, 0.3, 0.2)


def test_horizon_overrides_the_profile_for_clocks_past_90():
    """Extra time runs off the 90-minute market clock, so the caller hands
    the model an explicit remaining-share instead of the fitted profile."""
    profile = [1.0 - t / 90.0 for t in range(91)]
    m = model.InPlayModel(1.4, 1.1, w=0.0, profile=profile)
    # at t = 105 the profile is exhausted, so without a horizon nothing is left
    assert m.probs(105, 1, 1, 0.0, 0.0)["pD"] == 1.0
    # with 15 minutes still to play the draw is no longer certain
    live = m.probs(105, 1, 1, 0.0, 0.0, horizon=15.0 / 90.0)
    assert live["pD"] < 1.0 and live["pH"] > 0.0


def test_red_card_swings_the_price_when_multipliers_are_supplied():
    params = {"w": 0.0, "red": {"self": 0.6, "opp": 1.3}}
    m = model.InPlayModel.from_params(1.4, 1.2, params)
    even = m.probs(40, 0, 0, 0.0, 0.0)
    home_down = m.probs(40, 0, 0, 0.0, 0.0, red_h=1)
    assert home_down["pH"] < even["pH"]
    assert home_down["pA"] > even["pA"]
