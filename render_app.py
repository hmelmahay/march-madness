"""
Render-hosted dashboard for March Madness Squares.

The local scheduler (main.py on Steve's Mac) pushes game data here via
POST /update every 10 minutes.  This app serves a live dashboard to all
participants at a stable public URL.
"""

import json
import logging
import os
from datetime import datetime

import pytz
from flask import Flask, Response, request

from config import ROUNDS, TOTAL_POOL
from logic import build_leaderboard, total_paid_out

log = logging.getLogger(__name__)
app = Flask(__name__)
MT = pytz.timezone("America/Denver")

SECRET = os.environ.get("DASHBOARD_SECRET", "")

# In-memory state — repopulated by the local scheduler every 10 minutes.
# If Render restarts, the next scheduler tick automatically restores it.
_state: dict = {
    "completed_games": [],
    "updated_at": None,
}

# ── HTML templates ─────────────────────────────────────────────────────────────

_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="60">
  <title>March Madness Squares</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #f0f2f5; font-family: Arial, sans-serif; padding: 20px; }}
    .card {{ background: #fff; border-radius: 10px; overflow: hidden;
             box-shadow: 0 2px 8px rgba(0,0,0,.12); max-width: 700px;
             margin: 0 auto 20px; }}
    .header {{ background: linear-gradient(135deg,#1a237e 0%,#4a148c 100%);
               padding: 28px 28px 20px; text-align: center; color: #fff; }}
    .header h1 {{ font-size: 22px; letter-spacing: 1px; }}
    .header .sub {{ color: #ce93d8; font-size: 13px; margin-top: 6px; }}
    .live-badge {{ display: inline-block; background: #e53935; color: #fff;
                   font-size: 11px; font-weight: bold; padding: 2px 8px;
                   border-radius: 20px; letter-spacing: 1px; margin-top: 8px; }}
    .refresh-note {{ color: #ce93d8; font-size: 11px; margin-top: 4px; }}
    .section-head {{ background: #4a148c; color: #fff; font-size: 12px;
                     font-weight: bold; letter-spacing: 1px; padding: 9px 14px; }}
    .section-head.lb {{ background: #1a237e; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ background: #f3e5f5; color: #666; font-size: 11px;
          padding: 7px 12px; text-align: left; }}
    th.r {{ text-align: right; }}
    td {{ padding: 8px 12px; font-size: 13px; border-bottom: 1px solid #f5f5f5; }}
    td.r {{ text-align: right; }}
    td.score {{ text-align: center; color: #555; }}
    td.winner {{ color: #1a237e; font-weight: bold; }}
    td.owner {{ color: #4a148c; font-weight: bold; }}
    td.money {{ color: #2e7d32; font-weight: bold; text-align: right; }}
    td.dimmed {{ color: #aaa; }}
    .stats {{ display: flex; padding: 16px 20px; background: #f3e5f5;
              justify-content: space-around; text-align: center; }}
    .stat-val {{ font-size: 22px; font-weight: bold; color: #4a148c; }}
    .stat-val.blue {{ color: #1a237e; }}
    .stat-label {{ font-size: 11px; color: #7b1fa2; margin-top: 2px; }}
    .progress-wrap {{ padding: 0 20px 14px; background: #f3e5f5; }}
    .bar-bg {{ background: #e1bee7; border-radius: 20px; height: 7px; overflow: hidden; }}
    .bar-fill {{ background: linear-gradient(90deg,#7b1fa2,#4a148c);
                 height: 7px; border-radius: 20px; }}
    .bar-label {{ font-size: 11px; color: #888; margin-top: 4px; text-align: center; }}
    .none {{ padding: 18px; color: #aaa; font-size: 13px; text-align: center; }}
    tr:nth-child(even) td {{ background: #fafafa; }}
    tr:nth-child(odd)  td {{ background: #fff; }}
    .gold td {{ background: #fffde7 !important; }}
    .updated {{ text-align: center; color: #aaa; font-size: 11px; padding: 10px; }}
  </style>
</head>
<body>

<div class="card">
  <div class="header">
    <div style="font-size:30px;">&#127936;</div>
    <h1>MARCH MADNESS SQUARES</h1>
    <div class="sub">{date_label}</div>
    <div class="live-badge">&#128308; LIVE</div>
    <div class="refresh-note">Auto-refreshes every 60 seconds</div>
  </div>

  {rounds_html}

  <div class="section-head lb">&#127942; CUMULATIVE LEADERBOARD</div>
  <table>
    <tr>
      <th style="width:36px;">#</th>
      <th>Name</th>
      <th class="r">Winnings</th>
      <th class="r">Wins</th>
    </tr>
    {leaderboard_rows}
  </table>

  <div class="stats">
    <div>
      <div class="stat-val">${paid:,}</div>
      <div class="stat-label">PAID OUT</div>
    </div>
    <div>
      <div class="stat-val blue">${remaining:,}</div>
      <div class="stat-label">STILL IN POOL</div>
    </div>
  </div>
  <div class="progress-wrap">
    <div class="bar-bg">
      <div class="bar-fill" style="width:{pct_paid:.0f}%;"></div>
    </div>
    <div class="bar-label">${paid:,} of ${total:,} paid out ({pct_paid:.0f}%)</div>
  </div>

  <div class="updated">Last updated: {updated_at}</div>
</div>

</body>
</html>
"""

_ROUND_SECTION = """\
  <div class="section-head">&#127936; {rname_upper} &nbsp;
    <span style="font-weight:normal;opacity:.75;">${payout} per game</span>
  </div>
  <table>
    <tr>
      <th>Winner</th><th>Score</th><th>Loser</th>
      <th>Square Winner</th><th class="r">Payout</th>
    </tr>
    {rows}
  </table>
"""

_GAME_ROW = """\
    <tr>
      <td class="winner">{winner}</td>
      <td class="score">{ws}&ndash;{ls}</td>
      <td class="dimmed">{loser}</td>
      <td class="owner">{owner}</td>
      <td class="money">${payout:,}</td>
    </tr>
"""

_LB_ROW = """\
    <tr{gold}>
      <td class="dimmed">{medal}{rank}</td>
      <td style="font-weight:{w};color:{nc};">{name}</td>
      <td class="r" style="font-weight:bold;color:{mc};">{total}</td>
      <td class="r dimmed">{wins}</td>
    </tr>
"""


def _render() -> str:
    all_games = _state["completed_games"]
    now_mt = datetime.now(MT)
    today_str = now_mt.date().isoformat()
    today_games = [g for g in all_games if g.get("date") == today_str]

    # Group today's games by round
    by_round: dict = {}
    for g in sorted(today_games, key=lambda x: (x.get("round", 0), x.get("date", ""))):
        by_round.setdefault(g["round"], []).append(g)

    round_names = {r["number"]: r["name"] for r in ROUNDS}

    rounds_html = ""
    if by_round:
        for rnum in sorted(by_round):
            rname = round_names.get(rnum, f"Round {rnum}")
            payout = next((r["payout_per_game"] for r in ROUNDS if r["number"] == rnum), 0)
            rows = "".join(
                _GAME_ROW.format(
                    winner=g["winner_name"], ws=g["winner_score"],
                    loser=g["loser_name"],   ls=g["loser_score"],
                    owner=g["square_owner"], payout=g["payout"],
                )
                for g in by_round[rnum]
            )
            rounds_html += _ROUND_SECTION.format(
                rname_upper=rname.upper(), payout=f"{payout:,}", rows=rows
            )
    else:
        rounds_html = '<div class="none">No completed games yet today — check back soon!</div>'

    leaderboard = build_leaderboard(all_games)
    medals = {1: "&#127947;", 2: "&#129352;", 3: "&#129353;"}
    lb_rows = ""
    for e in leaderboard:
        has_won = e["total"] > 0
        medal = medals.get(e["rank"], "") if has_won else ""
        wins_str = f"{e['wins']} win{'s' if e['wins'] != 1 else ''}" if e["wins"] > 0 else "-"
        lb_rows += _LB_ROW.format(
            gold=' class="gold"' if e["rank"] == 1 and has_won else "",
            medal=medal, rank=e["rank"],
            name=e["name"],
            w="bold" if has_won else "normal",
            nc="#1a237e" if has_won else "#aaa",
            total=f"${e['total']:,}" if has_won else "-",
            mc="#2e7d32" if has_won else "#ccc",
            wins=wins_str,
        )

    paid = total_paid_out(all_games)
    remaining = TOTAL_POOL - paid
    pct_paid = (paid / TOTAL_POOL * 100) if TOTAL_POOL else 0

    if _state["updated_at"]:
        try:
            updated_dt = datetime.fromisoformat(_state["updated_at"])
            if updated_dt.tzinfo is None:
                updated_dt = MT.localize(updated_dt)
            else:
                updated_dt = updated_dt.astimezone(MT)
            updated_str = updated_dt.strftime("%b %d, %Y  %I:%M %p MT")
        except Exception:
            updated_str = str(_state["updated_at"])
    else:
        updated_str = "Waiting for first update from tracker..."

    return _HTML.format(
        date_label=now_mt.strftime("%B %d, %Y"),
        rounds_html=rounds_html,
        leaderboard_rows=lb_rows,
        paid=paid, remaining=remaining,
        pct_paid=pct_paid, total=TOTAL_POOL,
        updated_at=updated_str,
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    return Response(_render(), mimetype="text/html")


@app.route("/update", methods=["POST"])
def update():
    if not SECRET:
        return Response(
            json.dumps({"error": "DASHBOARD_SECRET not configured on server"}),
            status=500, mimetype="application/json",
        )
    data = request.get_json(silent=True)
    if not data or data.get("secret") != SECRET:
        return Response(
            json.dumps({"error": "unauthorized"}),
            status=401, mimetype="application/json",
        )
    _state["completed_games"] = data.get("completed_games", [])
    _state["updated_at"] = data.get("updated_at")
    log.info("Dashboard updated: %d games", len(_state["completed_games"]))
    return Response(
        json.dumps({"ok": True, "games": len(_state["completed_games"])}),
        mimetype="application/json",
    )


@app.route("/health")
def health():
    return Response(json.dumps({"status": "ok"}), mimetype="application/json")
