"""
March Madness Squares Tracker — main entry point.

Usage:
  python main.py            # run the scheduler (normal mode)
  python main.py --fetch    # one-shot fetch right now, saves draft if new games found
  python main.py --dry-run  # fetch + print draft without saving to Gmail
  python main.py --status   # print current leaderboard and game counts
"""

import argparse
import logging
import os
import sys
from datetime import datetime

import pytz
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

import espn
import logic
import store
import server
from mailer import create_draft

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("tracker.log"),
    ],
)
log = logging.getLogger(__name__)

MT = pytz.timezone("America/Denver")


# ── Render push ───────────────────────────────────────────────────────────────

def push_to_render(all_games: list) -> None:
    """Push current game state to the Render dashboard every tick."""
    render_url = os.environ.get("RENDER_URL", "").rstrip("/")
    secret = os.environ.get("DASHBOARD_SECRET", "")
    if not render_url or not secret:
        return  # Render not configured yet — skip silently
    try:
        resp = requests.post(
            f"{render_url}/update",
            json={
                "secret": secret,
                "completed_games": all_games,
                "updated_at": datetime.now(MT).isoformat(),
            },
            timeout=15,
        )
        if resp.status_code == 200:
            log.info("Render dashboard updated (%d games).", len(all_games))
        else:
            log.warning("Render push returned %d: %s", resp.status_code, resp.text[:120])
    except Exception as exc:
        log.warning("Render push failed: %s", exc)


# ── Core tick ─────────────────────────────────────────────────────────────────

def tick(dry_run: bool = False) -> None:
    """Fetch new scores, process them, and save a final Gmail draft when the day's games are done."""
    known_ids = store.get_known_game_ids()
    new_games = espn.fetch_new_games(known_ids)

    if new_games:
        for game in new_games:
            logic.process_game(game)
            store.save_game(game)
            log.info(
                "  %s %d vs %s %d  -->  %s  ($%d)",
                game["winner_name"], game["winner_score"],
                game["loser_name"], game["loser_score"],
                game["square_owner"], game["payout"],
            )
    else:
        log.info("No new completed games found.")

    # Fix any games stored with wrong (future) UTC dates
    corrections = espn.get_date_corrections(store.get_completed_games())
    fixed = store.apply_date_corrections(corrections)
    if fixed:
        log.info("Fixed dates for %d stored game(s).", fixed)

    # Draft logic: only send once per day, after all games are finished
    today_str = datetime.now(MT).date().isoformat()

    # Always push current state to Render (even if draft already sent today)
    push_to_render(store.get_completed_games())

    if store.get_last_drafted_date() == today_str:
        log.info("Draft already saved for today.")
        return

    all_games = store.get_completed_games()
    today_games = [g for g in all_games if g.get("date") == today_str]

    if not today_games:
        return  # no tournament games today yet

    if espn.has_active_games_today():
        log.info("Games still in progress — will draft when they finish.")
        return

    # All done for today — save the final draft
    log.info("All today's games complete. Saving final draft...")
    success = create_draft(today_games, all_games, dry_run=dry_run)
    if success:
        if not dry_run:
            store.mark_drafted(today_str)
        log.info("Final draft saved for %s.", today_str)
    else:
        log.error("Failed to save draft.")


# ── CLI commands ───────────────────────────────────────────────────────────────

def cmd_status() -> None:
    from config import ROUNDS
    all_games = store.get_completed_games()
    print("\n=== March Madness Squares — Status ===\n")
    for rnd in ROUNDS:
        count = sum(1 for g in all_games if g["round"] == rnd["number"])
        complete = "✓" if logic.is_round_complete(rnd["number"], all_games) else " "
        print(f"  [{complete}] {rnd['name']:<22} {count:2}/{rnd['games_expected']} games")
    print()

    board = logic.build_leaderboard(all_games)
    paid = logic.total_paid_out(all_games)
    print(f"  Total paid out: ${paid:,}\n")
    print("  Leaderboard (winners only):")
    for entry in board:
        if entry["total"] > 0:
            print(f"    {entry['rank']:2}. {entry['name']:<14}  ${entry['total']:>6,}  ({entry['wins']} win(s))")
    print()


# ── Scheduler ─────────────────────────────────────────────────────────────────

def run_scheduler(dry_run: bool = False) -> None:
    interval = int(os.environ.get("FETCH_INTERVAL_MINUTES", 30))
    port = int(os.environ.get("DASHBOARD_PORT", 5000))
    server.start(port=port)

    log.info("Starting scheduler — fetching every %d minutes (Mountain Time)", interval)

    scheduler = BlockingScheduler(timezone=MT)
    scheduler.add_job(
        tick,
        "interval",
        minutes=interval,
        kwargs={"dry_run": dry_run},
        id="fetch_scores",
        next_run_time=datetime.now(MT),  # run immediately on startup
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="March Madness Squares Tracker")
    parser.add_argument("--fetch",   action="store_true", help="One-shot fetch, save draft if new games")
    parser.add_argument("--dry-run", action="store_true", help="Fetch + print draft, don't save to Gmail")
    parser.add_argument("--status",  action="store_true", help="Print current status and leaderboard")
    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.fetch or args.dry_run:
        tick(dry_run=args.dry_run)
    else:
        run_scheduler()


if __name__ == "__main__":
    main()
