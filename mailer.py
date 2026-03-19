"""
Email generation and Gmail draft creation via IMAP.
Saves to your Drafts folder — you review and hit Send.
All recipients are BCC so nobody sees the full list.
"""

import imaplib
import logging
import os
import time
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import PARTICIPANT_EMAILS, ROUNDS, TOTAL_POOL
from logic import build_leaderboard, total_paid_out

log = logging.getLogger(__name__)

# ── HTML template ──────────────────────────────────────────────────────────────

_HTML = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f5;padding:24px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.12);">

  <!-- HEADER -->
  <tr>
    <td style="background:linear-gradient(135deg,#1a237e 0%,#4a148c 100%);padding:30px 32px;text-align:center;">
      <div style="font-size:32px;margin-bottom:6px;">&#127936;</div>
      <div style="color:#ffffff;font-size:24px;font-weight:bold;letter-spacing:1px;">MARCH MADNESS SQUARES</div>
      <div style="color:#ce93d8;font-size:14px;margin-top:6px;">{date_label} Update</div>
    </td>
  </tr>

  <!-- INTRO -->
  <tr>
    <td style="padding:24px 32px 8px;">
      <p style="margin:0;color:#333;font-size:15px;">Hi Everyone,</p>
      <p style="color:#555;font-size:14px;line-height:1.6;">Here's today's update on our March Madness Squares pool. Check the leaderboard below to see where you stand!</p>
    </td>
  </tr>

  {rounds_html}

  <!-- LEADERBOARD -->
  <tr>
    <td style="padding:8px 32px 8px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="background:#1a237e;color:#ffffff;font-size:13px;font-weight:bold;
                     letter-spacing:1px;padding:10px 14px;border-radius:6px 6px 0 0;">
            &#127942; CUMULATIVE LEADERBOARD
          </td>
        </tr>
      </table>
      <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e0e0e0;border-top:none;border-radius:0 0 6px 6px;overflow:hidden;">
        <tr style="background:#ede7f6;">
          <th style="padding:8px 12px;text-align:left;font-size:12px;color:#666;width:36px;">#</th>
          <th style="padding:8px 12px;text-align:left;font-size:12px;color:#666;">Name</th>
          <th style="padding:8px 12px;text-align:right;font-size:12px;color:#666;">Winnings</th>
          <th style="padding:8px 12px;text-align:right;font-size:12px;color:#666;">Wins</th>
        </tr>
        {leaderboard_rows}
      </table>
    </td>
  </tr>

  <!-- POOL STATS -->
  <tr>
    <td style="padding:16px 32px 8px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3e5f5;border-radius:8px;">
        <tr>
          <td style="padding:16px;text-align:center;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="text-align:center;width:50%;border-right:1px solid #ce93d8;">
                  <div style="font-size:22px;font-weight:bold;color:#4a148c;">${paid:,}</div>
                  <div style="font-size:11px;color:#7b1fa2;margin-top:2px;">PAID OUT</div>
                </td>
                <td style="text-align:center;width:50%;">
                  <div style="font-size:22px;font-weight:bold;color:#1a237e;">${remaining:,}</div>
                  <div style="font-size:11px;color:#283593;margin-top:2px;">STILL IN POOL</div>
                </td>
              </tr>
            </table>
            <div style="margin-top:12px;background:#e1bee7;border-radius:20px;height:8px;overflow:hidden;">
              <div style="background:linear-gradient(90deg,#7b1fa2,#4a148c);height:8px;width:{pct_paid:.0f}%;border-radius:20px;"></div>
            </div>
            <div style="font-size:11px;color:#888;margin-top:4px;">${paid:,} of ${total:,} paid out ({pct_paid:.0f}%)</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="padding:20px 32px 28px;text-align:center;">
      <p style="margin:0;color:#888;font-size:13px;">Good luck the rest of the way! &#127952;</p>
    </td>
  </tr>

</table>
</td></tr></table>
</body>
</html>
"""

_ROUND_BLOCK = """\
  <tr>
    <td style="padding:16px 32px 8px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="background:#4a148c;color:#ffffff;font-size:13px;font-weight:bold;
                     letter-spacing:1px;padding:10px 14px;border-radius:6px 6px 0 0;">
            &#127936; {rname_upper} &nbsp;<span style="font-weight:normal;opacity:.75;">${payout} per game</span>
          </td>
        </tr>
      </table>
      <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e0e0e0;border-top:none;border-radius:0 0 6px 6px;overflow:hidden;">
        <tr style="background:#f3e5f5;">
          <th style="padding:8px 12px;text-align:left;font-size:12px;color:#666;">Winner</th>
          <th style="padding:8px 12px;text-align:center;font-size:12px;color:#666;">Score</th>
          <th style="padding:8px 12px;text-align:left;font-size:12px;color:#666;">Loser</th>
          <th style="padding:8px 12px;text-align:left;font-size:12px;color:#666;">Square Winner</th>
          <th style="padding:8px 12px;text-align:right;font-size:12px;color:#666;">Payout</th>
        </tr>
        {game_rows}
      </table>
    </td>
  </tr>
"""

_GAME_ROW = """\
        <tr style="background:{bg};">
          <td style="padding:9px 12px;font-size:13px;font-weight:bold;color:#1a237e;">{winner}</td>
          <td style="padding:9px 12px;font-size:13px;text-align:center;color:#555;">{w_score}&ndash;{l_score}</td>
          <td style="padding:9px 12px;font-size:13px;color:#777;">{loser}</td>
          <td style="padding:9px 12px;font-size:13px;color:#4a148c;font-weight:bold;">{owner}</td>
          <td style="padding:9px 12px;font-size:13px;text-align:right;color:#2e7d32;font-weight:bold;">${payout}</td>
        </tr>
"""

_LB_ROW = """\
        <tr style="background:{bg};">
          <td style="padding:9px 12px;font-size:13px;color:#888;">{medal}{rank}</td>
          <td style="padding:9px 12px;font-size:14px;font-weight:{weight};color:{name_color};">{name}</td>
          <td style="padding:9px 12px;font-size:14px;text-align:right;font-weight:bold;color:{money_color};">{total}</td>
          <td style="padding:9px 12px;font-size:12px;text-align:right;color:#888;">{wins}</td>
        </tr>
"""


# ── Builders ───────────────────────────────────────────────────────────────────

def _build_rounds_html(by_round: dict, round_names: dict) -> str:
    html = ""
    for rnum in sorted(by_round):
        rname = round_names.get(rnum, f"Round {rnum}")
        payout = next((r["payout_per_game"] for r in ROUNDS if r["number"] == rnum), 0)
        game_rows = ""
        for i, g in enumerate(by_round[rnum]):
            bg = "#ffffff" if i % 2 == 0 else "#fafafa"
            game_rows += _GAME_ROW.format(
                bg=bg,
                winner=g["winner_name"], w_score=g["winner_score"],
                loser=g["loser_name"],   l_score=g["loser_score"],
                owner=g["square_owner"], payout=f"{g['payout']:,}",
            )
        html += _ROUND_BLOCK.format(
            rname_upper=rname.upper(), payout=f"{payout:,}",
            game_rows=game_rows,
        )
    return html


def _build_leaderboard_html(leaderboard: list[dict]) -> str:
    medals = {1: "&#127947;", 2: "&#129352;", 3: "&#129353;"}
    rows = ""
    for i, entry in enumerate(leaderboard):
        has_won = entry["total"] > 0
        bg = "#fffde7" if entry["rank"] == 1 and has_won else ("#ffffff" if i % 2 == 0 else "#fafafa")
        medal = medals.get(entry["rank"], "") if has_won else ""
        wins_str = f"{entry['wins']} win{'s' if entry['wins'] != 1 else ''}" if entry["wins"] > 0 else "-"
        rows += _LB_ROW.format(
            bg=bg,
            medal=medal, rank=entry["rank"],
            name=entry["name"],
            weight="bold" if has_won else "normal",
            name_color="#1a237e" if has_won else "#999",
            total=f"${entry['total']:,}" if has_won else "-",
            money_color="#2e7d32" if has_won else "#ccc",
            wins=wins_str,
        )
    return rows


def generate_html(games_today: list[dict], all_games: list[dict]) -> str:
    leaderboard = build_leaderboard(all_games)
    paid = total_paid_out(all_games)
    remaining = TOTAL_POOL - paid
    pct_paid = (paid / TOTAL_POOL * 100) if TOTAL_POOL else 0

    by_round: dict[int, list[dict]] = {}
    for g in sorted(games_today, key=lambda x: (x.get("round", 0), x.get("date", ""))):
        by_round.setdefault(g["round"], []).append(g)

    round_names = {r["number"]: r["name"] for r in ROUNDS}

    return _HTML.format(
        date_label=date.today().strftime("%B %d, %Y"),
        rounds_html=_build_rounds_html(by_round, round_names),
        leaderboard_rows=_build_leaderboard_html(leaderboard),
        paid=paid, remaining=remaining,
        pct_paid=pct_paid, total=TOTAL_POOL,
    )


def generate_plaintext(games_today: list[dict], all_games: list[dict]) -> str:
    """Fallback plain-text version for email clients that don't render HTML."""
    leaderboard = build_leaderboard(all_games)
    paid = total_paid_out(all_games)
    remaining = TOTAL_POOL - paid

    by_round: dict[int, list[dict]] = {}
    for g in sorted(games_today, key=lambda x: (x.get("round", 0), x.get("date", ""))):
        by_round.setdefault(g["round"], []).append(g)

    round_names = {r["number"]: r["name"] for r in ROUNDS}
    lines = ["Hi Everyone,", "", "Here's today's update on our March Madness Squares pool!", ""]

    for rnum in sorted(by_round):
        rname = round_names.get(rnum, f"Round {rnum}")
        payout = next((r["payout_per_game"] for r in ROUNDS if r["number"] == rnum), 0)
        lines += ["-" * 50, f"{rname.upper()}  (${payout} per game)", "-" * 50]
        for g in by_round[rnum]:
            lines.append(
                f"  {g['winner_name']} {g['winner_score']}, "
                f"{g['loser_name']} {g['loser_score']}"
                f"  -->  {g['square_owner']} wins ${g['payout']:,}"
            )
        lines.append("")

    lines += ["-" * 50, "CUMULATIVE LEADERBOARD", "-" * 50]
    for entry in leaderboard:
        wins_str = f"  ({entry['wins']} win{'s' if entry['wins'] != 1 else ''})" if entry["wins"] > 0 else ""
        lines.append(f"  {entry['rank']:2}. {entry['name']:<14}  ${entry['total']:,}{wins_str}")

    lines += ["", "-" * 50,
              f"Total Paid Out: ${paid:,} / ${TOTAL_POOL:,}",
              f"Still in Pool:  ${remaining:,}", "-" * 50, "",
              "Good luck the rest of the way!"]
    return "\n".join(lines)


# ── Draft sender ───────────────────────────────────────────────────────────────

def create_draft(games_today: list[dict], all_games: list[dict], dry_run: bool = False) -> bool:
    """Save a draft email to Gmail's Drafts folder via IMAP. Returns True on success."""
    sender = os.environ.get("GMAIL_EMAIL", "").strip()
    password = os.environ.get("GMAIL_PASSWORD", "").replace("\u00a0", "").replace(" ", "")

    if not sender or not password:
        log.error("GMAIL_EMAIL or GMAIL_PASSWORD not set")
        return False

    today_label = date.today().strftime("%B %d, %Y")
    subject = f"March Madness Squares - {today_label}"

    all_recipients = list(PARTICIPANT_EMAILS) + [sender]
    all_recipients = list(dict.fromkeys(all_recipients))

    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = sender
    msg["Bcc"] = ", ".join(r for r in all_recipients if r != sender)
    msg["Subject"] = subject
    msg.attach(MIMEText(generate_plaintext(games_today, all_games), "plain", "utf-8"))
    msg.attach(MIMEText(generate_html(games_today, all_games), "html", "utf-8"))

    if dry_run:
        print(f"\n[DRY RUN] Subject: {subject}")
        print(f"[DRY RUN] BCC: {len(all_recipients)} recipients")
        print("[DRY RUN] HTML draft generated (open dry_run_preview.html to preview)")
        with open("dry_run_preview.html", "w") as f:
            f.write(generate_html(games_today, all_games))
        return True

    try:
        log.info("Saving draft to Gmail...")
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(sender, password)
        imap.append(
            "[Gmail]/Drafts",
            "\\Draft",
            imaplib.Time2Internaldate(time.time()),
            msg.as_string().encode("utf-8"),
        )
        imap.logout()
        log.info("Draft saved: '%s' (%d recipients)", subject, len(all_recipients))
        return True
    except imaplib.IMAP4.error:
        log.error("Gmail IMAP auth failed. Check GMAIL_EMAIL and GMAIL_PASSWORD (use an App Password).")
        return False
    except Exception as exc:
        log.error("Failed to save draft: %s", exc)
        return False
