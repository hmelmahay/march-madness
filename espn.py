"""
ESPN API client — fetch completed NCAA tournament games.
"""

import logging
import time
from datetime import date, timedelta

from typing import Optional

import requests

from config import ESPN_SCOREBOARD_URL, ROUNDS, ROUND_KEYWORD_MAP

log = logging.getLogger(__name__)

TIMEOUT = 15   # seconds per request
RETRY_WAIT = 5 # seconds between retries


def _get(url: str, params: dict) -> Optional[dict]:
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            log.warning("ESPN request failed (attempt %d/3): %s", attempt + 1, exc)
            if attempt < 2:
                time.sleep(RETRY_WAIT)
    return None


def _detect_round(event: dict) -> Optional[int]:
    """
    Return the tournament round number (1-6) by inspecting ESPN event data,
    or None if this doesn't look like a main-bracket tournament game.
    First Four play-in games are excluded (they don't use the 10×10 grid).
    """
    for comp in event.get("competitions", []):
        for note in comp.get("notes", []):
            headline = note.get("headline", "").lower()

            # Exclude "First Four" play-in games
            if "first four" in headline:
                return None

            # Match specific round keywords (ordered most-specific first)
            for keyword, rnum in ROUND_KEYWORD_MAP.items():
                if keyword in headline:
                    return rnum

    # Fall back to date-based detection (safe because First Four dates ≠ round dates)
    game_date_str = event.get("date", "")[:10]  # "YYYY-MM-DD"
    for rnd in ROUNDS:
        if game_date_str in rnd["dates"]:
            return rnd["number"]

    return None


def _parse_game(event: dict, round_number: int) -> Optional[dict]:
    """
    Convert an ESPN event dict into our internal game dict.
    Returns None if data is incomplete or game not finished.
    """
    comps = event.get("competitions", [])
    if not comps:
        return None
    comp = comps[0]

    status = comp.get("status", {})
    if not status.get("type", {}).get("completed", False):
        return None

    competitors = comp.get("competitors", [])
    if len(competitors) != 2:
        return None

    # ESPN labels home/away; we just need winner & loser
    teams = []
    for c in competitors:
        score_str = c.get("score", "0")
        try:
            score = int(score_str)
        except ValueError:
            return None
        teams.append({
            "name": c.get("team", {}).get("displayName", "Unknown"),
            "score": score,
            "winner": c.get("winner", False),
        })

    if teams[0]["score"] == teams[1]["score"]:
        log.warning("Tie game detected for %s — skipping", event.get("id"))
        return None

    winner = next((t for t in teams if t["winner"]), max(teams, key=lambda t: t["score"]))
    loser = next((t for t in teams if not t["winner"]), min(teams, key=lambda t: t["score"]))

    # If the "winner" flag isn't set, pick by score
    if teams[0]["score"] == teams[1]["score"]:
        return None
    if winner["score"] < loser["score"]:
        winner, loser = loser, winner

    from config import ROUNDS
    rnd_cfg = next((r for r in ROUNDS if r["number"] == round_number), None)
    payout = rnd_cfg["payout_per_game"] if rnd_cfg else 0

    return {
        "espn_id": str(event.get("id", "")),
        "round": round_number,
        "winner_name": winner["name"],
        "winner_score": winner["score"],
        "loser_name": loser["name"],
        "loser_score": loser["score"],
        "payout": payout,
        "date": event.get("date", "")[:10],
        "square_owner": None,  # filled by logic.py
    }


def has_active_games_today() -> bool:
    """Return True if any tournament games today are still in-progress or scheduled."""
    today_str = date.today().strftime("%Y%m%d")
    data = _get(ESPN_SCOREBOARD_URL, params={"dates": today_str, "limit": 50})
    if not data:
        return False
    for event in data.get("events", []):
        if _detect_round(event) is None:
            continue
        comp = event.get("competitions", [{}])[0]
        if not comp.get("status", {}).get("type", {}).get("completed", False):
            return True  # at least one game still going
    return False


def fetch_new_games(known_ids: set[str]) -> list[dict]:
    """
    Poll ESPN for completed tournament games not yet in our store.
    Checks today and yesterday to catch late-finishing games.
    """
    new_games: list[dict] = []
    dates_to_check: list[str] = []

    today = date.today()
    for delta in range(2):  # today and yesterday
        d = today - timedelta(days=delta)
        dates_to_check.append(d.strftime("%Y%m%d"))

    for date_str in dates_to_check:
        log.info("Fetching ESPN scoreboard for %s", date_str)
        data = _get(ESPN_SCOREBOARD_URL, params={"dates": date_str, "limit": 50})
        if not data:
            continue

        for event in data.get("events", []):
            espn_id = str(event.get("id", ""))
            if espn_id in known_ids:
                continue  # already processed

            round_number = _detect_round(event)
            if round_number is None:
                continue  # not a tournament game

            game = _parse_game(event, round_number)
            if game:
                new_games.append(game)
                known_ids.add(espn_id)
                log.info(
                    "New game: %s %d vs %s %d (Round %d)",
                    game["winner_name"], game["winner_score"],
                    game["loser_name"], game["loser_score"],
                    round_number,
                )

    return new_games
