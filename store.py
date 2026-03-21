"""
JSON-based persistence layer.
All state lives in data.json next to this file.
"""

import json
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data.json"

_DEFAULTS = {
    "completed_games": [],  # list of game dicts
    "last_drafted_date": None,  # "YYYY-MM-DD" of last day we saved a draft
}


def _load() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return dict(_DEFAULTS)


def _save(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Public API ─────────────────────────────────────────────────────────────────

def get_completed_games() -> list[dict]:
    return _load()["completed_games"]


def get_known_game_ids() -> set[str]:
    return {g["espn_id"] for g in get_completed_games()}


def save_game(game: dict) -> None:
    """Append a newly completed game."""
    data = _load()
    data["completed_games"].append(game)
    _save(data)


def get_last_drafted_date() -> str:
    return _load().get("last_drafted_date") or ""


def apply_date_corrections(corrections: dict) -> int:
    """Update stored game dates that were saved with wrong (UTC) dates. Returns fix count."""
    if not corrections:
        return 0
    data = _load()
    count = 0
    for game in data["completed_games"]:
        if game["espn_id"] in corrections:
            game["date"] = corrections[game["espn_id"]]
            count += 1
    if count:
        _save(data)
    return count


def mark_drafted(date_str: str) -> None:
    data = _load()
    data["last_drafted_date"] = date_str
    _save(data)


def dump() -> dict:
    """Return full data store (for debugging)."""
    return _load()
