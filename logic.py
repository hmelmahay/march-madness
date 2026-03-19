"""
Core game logic: winner calculation, leaderboard building, round completion.
"""

from config import GRID, ROUNDS, WINNER_AXIS, NAME_MAP


def display_name(key: str) -> str:
    return NAME_MAP.get(key, key)


def calculate_winner(winner_score: int, loser_score: int) -> str:
    """
    Grid lookup:
      - Row = loser's last digit (used directly as the row index)
      - Col = physical column position of winner's last digit in WINNER_AXIS
    Returns the owner name at that intersection.
    """
    winner_digit = winner_score % 10
    loser_digit = loser_score % 10
    col = WINNER_AXIS.index(winner_digit)
    row = loser_digit
    return GRID[row][col]


def process_game(game: dict) -> dict:
    """Attach square_owner (full display name) to a game dict (in-place and returned)."""
    game["square_owner"] = display_name(calculate_winner(game["winner_score"], game["loser_score"]))
    return game


def build_leaderboard(completed_games: list[dict]) -> list[dict]:
    """
    Returns a list of dicts sorted by total winnings (desc):
      [{"rank": 1, "name": "...", "total": 120, "wins": 2}, ...]
    Includes every unique owner seen in the grid.
    """
    totals: dict[str, int] = {}
    wins: dict[str, int] = {}

    for game in completed_games:
        owner = game.get("square_owner")
        payout = game.get("payout", 0)
        if owner:
            totals[owner] = totals.get(owner, 0) + payout
            wins[owner] = wins.get(owner, 0) + 1

    # Collect all unique display names from the grid so everyone appears
    all_keys: set[str] = set()
    for row in GRID:
        all_keys.update(row)

    rows = []
    for key in all_keys:
        full = display_name(key)
        rows.append({
            "name": full,
            "total": totals.get(full, 0),
            "wins": wins.get(full, 0),
        })

    rows.sort(key=lambda x: (-x["total"], x["name"]))
    for i, row in enumerate(rows, 1):
        row["rank"] = i

    return rows


def is_round_complete(round_number: int, completed_games: list[dict]) -> bool:
    """Return True when we have the expected number of games for this round."""
    rnd = next((r for r in ROUNDS if r["number"] == round_number), None)
    if not rnd:
        return False
    count = sum(1 for g in completed_games if g["round"] == round_number)
    return count >= rnd["games_expected"]


def games_for_round(round_number: int, completed_games: list[dict]) -> list[dict]:
    return [g for g in completed_games if g["round"] == round_number]


def total_paid_out(completed_games: list[dict]) -> int:
    return sum(g.get("payout", 0) for g in completed_games)
