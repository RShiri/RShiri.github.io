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
