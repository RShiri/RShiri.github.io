import pandas as pd

from backtest import transfers as tr

T, T1 = "2024-25", "2025-26"


def match(mid, season, date, team, player, minutes):
    return {"league": "ENG1", "season": season, "match_id": mid, "date": date, "team": team,
            "teamId": {"A": 1, "B": 2}[team], "player_id": player, "minutes": minutes}


def club_games(team, season, year, n, player=99):
    """n matches for a club, played by a filler so the club has a calendar."""
    return [match(f"{team}{season}{i}", season, f"{year}-{i + 1:02d}-15", team, player, 90) for i in range(n)]


def table(rows):
    return tr.transfers(tr.clubs_with_debut_share(pd.DataFrame(rows)), T, T1).set_index("player_id")


def test_stayed_is_not_a_transfer():
    r = table(club_games("A", T, 2024, 2) + club_games("A", T1, 2025, 2)).loc[99]
    assert r["status"] == "stayed" and pd.isna(r["success"])


def test_moved_and_played_is_a_success():
    rows = club_games("A", T, 2024, 2) + club_games("B", T1, 2025, 4, 98)
    rows += club_games("A", T, 2024, 1, 7) + club_games("B", T1, 2025, 4, 7)
    r = table(rows).loc[7]
    assert r["status"] == "moved" and r["success"] == 1


def test_moved_and_barely_played_is_a_failure():
    rows = club_games("A", T, 2024, 2) + club_games("B", T1, 2025, 4, 98)
    rows += club_games("A", T, 2024, 1, 7) + [match(f"B{T1}0", T1, "2025-01-15", "B", 7, 10)]
    r = table(rows).loc[7]
    assert r["status"] == "moved" and r["success"] == 0


def test_share_counts_only_matches_from_the_first_appearance():
    rows = club_games("A", T, 2024, 2) + club_games("B", T1, 2025, 4, 98)
    rows += club_games("A", T, 2024, 1, 7)
    rows += [match(f"B{T1}{i}", T1, f"2025-{i + 1:02d}-15", "B", 7, 90) for i in (2, 3)]   # joined late
    r = table(rows).loc[7]
    assert r["new_games_since"] == 2 and r["new_share_since"] == 1 and r["new_share_season"] == 0.5
    assert r["success"] == 1


def test_moved_uses_the_most_minutes_club_in_both_seasons():
    rows = club_games("A", T, 2024, 2) + club_games("B", T, 2024, 3, 98) + club_games("B", T1, 2025, 2)
    rows += club_games("A", T, 2024, 2, 7)
    rows += [match(f"B{T}2", T, "2024-03-15", "B", 7, 10),     # ended t at B, but A was his main club
             match(f"B{T1}0", T1, "2025-01-15", "B", 7, 90)]
    assert table(rows).loc[7, "status"] == "moved"


def test_gone_stays_out_of_the_success_rate():
    r = table(club_games("A", T, 2024, 2) + club_games("A", T1, 2025, 2, 98)).loc[99]
    assert r["status"] == "gone" and pd.isna(r["success"])
