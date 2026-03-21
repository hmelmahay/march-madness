"""
March Madness Squares - Configuration & Static Data
"""

# ── Grid ──────────────────────────────────────────────────────────────────────
# GRID[row][col]  →  row = loser's last digit, col = winner's last digit
GRID = [
    #  Col:  0         1         2         3         4         5         6         7         8         9
    ["Corey",  "Davis",  "Spille", "Garret", "STEVE",  "Spille", "Jabo",   "This",   "This",   "This"  ],  # Row 0
    ["4Hrse",  "Sports", "Madiso", "C.May",  "Shuter", "Corey",  "J.Brt",  "Shuter", "Lael",   "This"  ],  # Row 1
    ["J.Brt",  "Bailey", "4Hrse",  "Y.Mitc", "Y.Mitc", "Tanner", "Holst",  "StevQ",  "MC",     "Marko" ],  # Row 2
    ["Kalski", "Lael",   "Mike",   "Larsen", "Phil",   "Elizab", "Jabo",   "J.Brt",  "Mason",  "Shuter"],  # Row 3
    ["Sports", "4Hrse",  "Kalski", "RickB",  "Shuter", "Lael",   "Marko",  "Larsen", "Jenny",  "4Hrse" ],  # Row 4
    ["Spille", "Mallet", "STEVE",  "Kalski", "Corey",  "Rob",    "Lael",   "C.May",  "Holst",  "GarL"  ],  # Row 5
    ["Rob",    "Larsen", "C.May",  "Larsen", "Davis",  "Spille", "Marko",  "Sports", "Larsen", "Marko" ],  # Row 6
    ["Elizab", "J.Brt",  "4Hrse",  "Marko",  "J.Brt",  "Jabo",   "Kalski", "RickB",  "Robert", "This"  ],  # Row 7
    ["MC",     "Robert", "J.Brt",  "Yay.M",  "Yay.M",  "Rhodes", "RickB",  "Corey",  "4Hrse",  "C.May" ],  # Row 8
    ["Davis",  "MC",     "Corey",  "Rob",    "Rhodes", "Kalski", "Robert", "Max",    "Lael",   "MC"    ],  # Row 9
]

# Sanity check — must be 10×10
assert len(GRID) == 10 and all(len(row) == 10 for row in GRID), "Grid must be 10×10"

# ── Display name map ───────────────────────────────────────────────────────────
# Maps abbreviated grid keys → full display names shown in emails.
NAME_MAP = {
    "Corey":   "Corey Graham",
    "Davis":   "Davis",
    "Spille":  "Spille",
    "Garret":  "Garret B.",
    "GarL":    "Garrett Lip",
    "STEVE":   "Steve Burrill",
    "This":    "This Pool Sucks",
    "4Hrse":   "4 Horsemen",
    "Sports":  "Sports",
    "Madiso":  "Madison Lip",
    "C.May":   "C. May",
    "Shuter":  "Shuter",
    "J.Brt":   "J Baart",
    "Lael":    "Lael Graham",
    "Bailey":  "Bailey",
    "Y.Mitc":  "Yay Mitch",
    "Tanner":  "Tanner Lip",
    "Holst":   "Holst",
    "StevQ":   "Steve Q",
    "MC":      "MC",
    "Marko":   "Marko",
    "Kalski":  "Kalski",
    "Mike":    "Mike Lip",
    "Larsen":  "Larsen",
    "Phil":    "Phil V",
    "Elizab":  "Elizabeth",
    "Jabo":    "Jabo",
    "Mason":   "Mason",
    "RickB":   "Rick Bouska",
    "Jenny":   "Jenny Lip",
    "Rob":     "Rob R",
    "Mallet":  "Mallet",
    "Robert":  "Robert L",
    "Yay.M":   "Yay Mitch",
    "Rhodes":  "Rhodes",
    "Max":     "Max",
}

# ── Participants & Emails ──────────────────────────────────────────────────────
# All 22 participant emails (BCC recipients).
# Steve's email comes from the GMAIL_EMAIL env var and is included automatically.
PARTICIPANT_EMAILS = [
    "pokerdad123@gmail.com",
    "christopher.edmondsonjr@gmail.com",
    "lopez.mitch@gmail.com",
    "scott.kalski@gmail.com",
    "randy.larsen@gmail.com",
    "mamarkovich@gmail.com",
    "rlambardia@gmail.com",
    "sfshute@gmail.com",
    "lippmik1972@gmail.com",
    "jbaart@gmail.com",
    "brianalanholst@gmail.com",
    "craig.philip.cook@gmail.com",
    "rhodes.bevill@gmail.com",
    "rbouska@comcast.net",
    "davisburrill@icloud.com",
    "christopher_may@cable.comcast.com",
    "mike.spille@usa.net",
    "rcrigby@gmail.com",
    "sandpiper8643@outlook.com",
    "mc_and_janis@comcast.net",
    "mallett23@hotmail.com",
    "sq745@msn.com",
]

# ── Round configuration ────────────────────────────────────────────────────────
ROUNDS = [
    {
        "number": 1,
        "name": "Round 1",
        "games_expected": 32,
        "payout_per_game": 15,
        "dates": ["2026-03-19", "2026-03-20"],
        "email_deadline": "2026-03-20 22:00",  # Mountain Time
    },
    {
        "number": 2,
        "name": "Round 2",
        "games_expected": 16,
        "payout_per_game": 30,
        "dates": ["2026-03-21", "2026-03-22"],
        "email_deadline": "2026-03-22 22:00",
    },
    {
        "number": 3,
        "name": "Sweet 16",
        "games_expected": 8,
        "payout_per_game": 60,
        "dates": ["2026-03-27", "2026-03-28"],
        "email_deadline": "2026-03-28 22:00",
    },
    {
        "number": 4,
        "name": "Elite Eight",
        "games_expected": 4,
        "payout_per_game": 120,
        "dates": ["2026-03-29", "2026-03-30"],
        "email_deadline": "2026-03-30 22:00",
    },
    {
        "number": 5,
        "name": "Final Four",
        "games_expected": 2,
        "payout_per_game": 240,
        "dates": ["2026-04-03", "2026-04-04"],
        "email_deadline": "2026-04-04 22:00",
    },
    {
        "number": 6,
        "name": "National Championship",
        "games_expected": 1,
        "payout_per_game": 600,
        "dates": ["2026-04-07"],
        "email_deadline": "2026-04-07 22:00",
    },
]

# Physical column order of winner's last digit (left→right across the top of the grid).
# To find the column index for a given winner digit: WINNER_AXIS.index(digit)
# Rows are indexed directly by loser's last digit value (GRID[loser_digit][col]).
WINNER_AXIS = [2, 7, 4, 5, 3, 9, 8, 0, 6, 1]

TOTAL_POOL = 3000
ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"

# Map ESPN round-name keywords → round number
ROUND_KEYWORD_MAP = {
    "1st round": 1,
    "first round": 1,
    "2nd round": 2,
    "second round": 2,
    "round of 32": 2,
    "sweet 16": 3,
    "sweet sixteen": 3,
    "elite eight": 4,
    "elite 8": 4,
    "final four": 5,
    "national championship": 6,
    # NOTE: do NOT add bare "championship" — it appears in every ESPN game title
    # NOTE: "first four" play-in games are excluded in espn.py
}
