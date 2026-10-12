"""The scouting universe: which leagues Scout Finder covers.

FotMob league ids. `clubelo` is the country code ClubElo uses, for league strength.
Ids marked unverified were not checked against FotMob from where this was
written; `python -m pipeline.fetch_fotmob --check` prints the name FotMob
returns for each id so a wrong one shows up at once.
"""

LEAGUES = {
    # Big five
    "ENG1": {"fotmob": 47,  "name": "Premier League",        "clubelo": "ENG", "level": 1},
    "ESP1": {"fotmob": 87,  "name": "LaLiga",                "clubelo": "ESP", "level": 1},
    "ITA1": {"fotmob": 55,  "name": "Serie A",               "clubelo": "ITA", "level": 1},
    "GER1": {"fotmob": 54,  "name": "Bundesliga",            "clubelo": "GER", "level": 1},
    "FRA1": {"fotmob": 53,  "name": "Ligue 1",               "clubelo": "FRA", "level": 1},
    # Feeder leagues
    "POR1": {"fotmob": 61,  "name": "Liga Portugal",         "clubelo": "POR", "level": 1},
    "NED1": {"fotmob": 57,  "name": "Eredivisie",            "clubelo": "NED", "level": 1},
    "BEL1": {"fotmob": 40,  "name": "Belgian Pro League",    "clubelo": "BEL", "level": 1},
    "ENG2": {"fotmob": 48,  "name": "Championship",          "clubelo": "ENG", "level": 2},
    "BRA1": {"fotmob": 268, "name": "Serie A (Brazil)",      "clubelo": None,  "level": 1},
    "ARG1": {"fotmob": 112, "name": "Liga Profesional",      "clubelo": None,  "level": 1},
    # Home
    "ISR1": {"fotmob": 127, "name": "Ligat ha'Al",           "clubelo": "ISR", "level": 1},
}

# Calendar-year leagues: their "2026" season is labelled 2026, not 2025-26.
CALENDAR_YEAR = {"BRA1", "ARG1"}
