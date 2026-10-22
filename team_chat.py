"""The team chat file: data/team_chat.md.

One line per message, written only by B, TIPPY and MENTOR:

    [2026-10-22 14:00 ET] [B] mixed: he keeps the floor version more often than the full one. @TIPPY any ideas?

Nothing here talks to an AI or to the network. It only reads, writes, trims and archives text.
"""
import datetime as dt
import re
from pathlib import Path

NAMES = ("B", "TIPPY", "MENTOR")
MAX_LEN = 300          # characters per message
MAX_PER_HOUR = 3       # messages per AI per hour
KEEP_LINES = 200       # newest lines kept in the main file; older ones move to the archive
STAMP = "%Y-%m-%d %H:%M"
LINE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) ET\] \[(B|TIPPY|MENTOR)\] (.+)$")
HEADER = ("# Team chat. One line per message: [date time ET] [NAME] message.\n"
          "# Written by B, TIPPY and MENTOR, who read it once an hour. You can read it any time.\n")


def clean_message(text, limit=MAX_LEN):
    """One line, no square brackets (so nobody can forge a [date] [NAME] tag), at most 300 characters."""
    return re.sub(r"\s+", " ", str(text or "")).strip().replace("[", "(").replace("]", ")")[:limit].strip()


def format_line(ts, name, text):
    return f"[{ts.strftime(STAMP)} ET] [{name}] {clean_message(text)}"


def parse(text):
    """Valid chat lines only, oldest first. Anything else in the file (headers, hand-written notes) is ignored."""
    out = []
    for raw in str(text or "").splitlines():
        m = LINE.match(raw.rstrip())
        if m:
            out.append({"stamp": m.group(1), "ts": dt.datetime.strptime(m.group(1), STAMP), "name": m.group(2),
                        "text": m.group(3), "raw": raw.rstrip()})
    return out


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def messages(path):
    return parse(read(path))


def append(path, lines):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = read(p) or HEADER
    if not existing.endswith("\n"):
        existing += "\n"
    p.write_text(existing + "".join(l + "\n" for l in lines), encoding="utf-8")


def hour_count(msgs, name, now):
    """How many messages this AI posted in the last 60 minutes."""
    return sum(1 for m in msgs if m["name"] == name and now - dt.timedelta(minutes=60) < m["ts"] <= now)


def unseen(msgs, name, cursor):
    """Lines by the others that are newer than this AI's last read (cursor is a 'YYYY-MM-DD HH:MM' string)."""
    return [m for m in msgs if m["name"] != name and m["stamp"] > (cursor or "")]


def repeats(msgs, name, text, now, hours=24):
    """True if this AI already said (almost) the same thing in the last day."""
    norm = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower())
    new = norm(text)
    return any(m["name"] == name and now - dt.timedelta(hours=hours) < m["ts"] and norm(m["text"]) == new for m in msgs)


def remove_lines(path, raws):
    """Delete exact lines from the chat (used when the reviewer pulls a line). Returns how many were removed."""
    wanted = list(raws)
    if not wanted:
        return 0
    kept, removed = [], 0
    for line in read(path).splitlines():
        if line.rstrip() in wanted:
            wanted.remove(line.rstrip())
            removed += 1
        else:
            kept.append(line)
    Path(path).write_text("\n".join(kept) + "\n", encoding="utf-8")
    return removed


def trim(path, archive_dir, keep=KEEP_LINES):
    """Keep the newest `keep` lines; move older ones into data/chat_archive/<year>-W<week>.md. Returns how many moved."""
    msgs = messages(path)
    if len(msgs) <= keep:
        return 0
    old = msgs[:-keep]
    by_week = {}
    for m in old:
        year, week, _ = m["ts"].isocalendar()
        by_week.setdefault(f"{year}-W{week:02d}", []).append(m["raw"])
    archive = Path(archive_dir)
    archive.mkdir(parents=True, exist_ok=True)
    for name, lines in by_week.items():
        f = archive / f"{name}.md"
        f.write_text((read(f) or "# Archived team chat\n") .rstrip("\n") + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    old_raws = {m["raw"] for m in old}
    kept = [l for l in read(path).splitlines() if l.rstrip() not in old_raws]
    Path(path).write_text("\n".join(kept) + "\n", encoding="utf-8")
    return len(old)


def recent_text(path, n=8):
    return "\n".join(m["raw"] for m in messages(path)[-n:])


def week_text(path, archive_dir, now, days=7):
    """Everything said in the last `days` days, from the main file and the archive."""
    since = now - dt.timedelta(days=days)
    msgs = messages(path)
    for f in sorted(Path(archive_dir).glob("*.md")):
        msgs = parse(read(f)) + msgs
    return "\n".join(m["raw"] for m in sorted(msgs, key=lambda m: m["ts"]) if m["ts"] >= since)
