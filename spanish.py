"""The Spanish coach: small, adaptive, and measured.

One short Spanish item a day, sized to Jason's level. The code keeps the facts; the AIs (Tippy picks, the Mentor writes) use them
to decide how to teach him.

  * LEVEL (1-5) moves with his one-word answers: 'es easy', 'es ok', 'es hard'.
  * FORMAT (phrase, cognate, dialogue, fill) is chosen from what has actually worked: a format counts as working when he
    remembers what it taught when the phrase comes back for review.
  * REVIEW: every phrase returns after 1, 3, 7, 14 and 30 days, one at a time, on alternate days at most.

Nothing here talks to an AI or the network. State lives in state.json under "spanish".
"""
import datetime as dt
import re

LEVELS = {
    1: ("Survival", "one or two words, or a three-word phrase. Words he can half-guess from English (inspección, defecto, lote)."),
    2: ("Short and polite", "one short sentence, about 4 to 6 words, a polite work question or request."),
    3: ("Useful sentence", "one sentence of about 7 to 9 words that does a real job on the floor (ask, explain, confirm)."),
    4: ("Two lines", "a two-line exchange: a question and the answer he is likely to hear, 10 to 14 words in all."),
    5: ("His own words", "a sentence frame with one gap for him to fill with his own word, so he starts to build sentences."),
}
MAX_WORDS = {1: 4, 2: 6, 3: 9, 4: 14, 5: 14}
START_LEVEL = 2          # a little easy on purpose; the answers move it from here

FORMATS = {
    "phrase": "the phrase, how to say it, what it means, the moment to use it",
    "cognate": "start from an English work word he already knows and show its Spanish twin, then one sentence using it",
    "dialogue": "two short lines: what he says and the answer he is likely to hear",
    "fill": "a sentence with one gap; he completes it out loud with a word of his own",
}
FORMAT_MIN_LEVEL = {"phrase": 1, "cognate": 1, "dialogue": 3, "fill": 4}
INTERVALS = [1, 3, 7, 14, 30]  # days until the next review, by stage
BOX_CAP = 40
UP_AFTER_EASY = 2        # 'easy' answers in a row that move him up
UP_AFTER_STEADY = 7      # 'ok' or 'easy' answers in a row that move him up

SIGNAL_RE = re.compile(r"\b(?:es|sp|spanish|español)\b[\s:=-]*(too\s+)?(easy|ok|okay|good|fine|hard|difficult|tough)\b", re.I)
LOOSE_RE = re.compile(r"\b(spanish|español|phrase|frase)\b", re.I)
WORD_SIGNAL = {"easy": "easy", "ok": "ok", "okay": "ok", "good": "ok", "fine": "ok", "hard": "hard", "difficult": "hard", "tough": "hard"}


def fresh():
    return {"level": START_LEVEL, "easy_run": 0, "steady_run": 0, "box": [], "history": [], "stats": {}, "last": None,
            "last_mode": "new", "force_easy": False}


def get(state):
    sp = state.setdefault("spanish", fresh())
    for k, v in fresh().items():
        sp.setdefault(k, v)
    return sp


def parse_signal(text):
    """easy / ok / hard from 'es hard', 'Spanish: too easy', or 'down, the Spanish was hard'. None if he did not say."""
    t = (text or "")[:300]
    m = SIGNAL_RE.search(t)
    if m:
        return WORD_SIGNAL[m.group(2).lower()]
    if LOOSE_RE.search(t):
        m = re.search(r"\b(too\s+easy|easy|hard|difficult|confusing|too\s+much)\b", t, re.I)
        if m:
            w = m.group(1).lower()
            return "easy" if "easy" in w else "hard"
    return None


def _stat(sp, fmt):
    return sp["stats"].setdefault(fmt, {"taught": 0, "recall_ok": 0, "recall_fail": 0, "hard": 0, "easy": 0})


def _add_days(day, n):
    return str(dt.date.fromisoformat(day) + dt.timedelta(days=n))


def apply_signals(state, replies, today):
    """His 'es easy / ok / hard' answers apply to the last Spanish item he was sent. Returns the signals used."""
    sp = get(state)
    used = []
    for r in replies or []:
        if r.get("kind", "reply") != "reply":
            continue
        sig, last = parse_signal(r.get("text", "")), sp.get("last")
        if not sig or not last or last.get("answered"):
            continue
        last["answered"] = True
        st = _stat(sp, last["fmt"])
        item = next((b for b in sp["box"] if b["phrase"] == last["phrase"]), None)
        if sig == "hard":
            sp["level"] = max(1, sp["level"] - 1)
            sp["easy_run"], sp["steady_run"], sp["force_easy"] = 0, 0, True
            st["hard"] += 1
            if last["mode"] == "review":
                st["recall_fail"] += 1
                if item:
                    item["stage"], item["due"] = max(0, item["stage"] - 1), _add_days(today, 1)
        else:
            sp["force_easy"] = False
            sp["steady_run"] += 1
            sp["easy_run"] = sp["easy_run"] + 1 if sig == "easy" else 0
            st["easy"] += sig == "easy"
            if last["mode"] == "review":
                st["recall_ok"] += 1
                if item:
                    item["stage"] += 1
                    if item["stage"] >= len(INTERVALS):
                        sp["box"].remove(item)  # learned
                    else:
                        item["due"] = _add_days(today, INTERVALS[item["stage"]])
            if sp["level"] < max(LEVELS) and (sp["easy_run"] >= UP_AFTER_EASY or sp["steady_run"] >= UP_AFTER_STEADY):
                sp["level"] += 1
                sp["easy_run"], sp["steady_run"] = 0, 0
        sp["history"] = (sp["history"] + [{"date": today, "level": last["level"], "fmt": last["fmt"], "mode": last["mode"], "signal": sig}])[-30:]
        used.append(sig)
    return used


def due_item(state, today):
    sp = get(state)
    due = sorted((b for b in sp["box"] if b["due"] <= today), key=lambda b: b["due"])
    return due[0] if due else None


def choose_mode(state, today):
    """'review' when something is due and yesterday was not a review; else 'new'."""
    sp = get(state)
    if due_item(state, today) and sp.get("last_mode") != "review" and not sp.get("force_easy"):
        return "review"
    return "new"


def allowed_formats(level):
    return [f for f, lo in FORMAT_MIN_LEVEL.items() if level >= lo]


def suggest_format(state):
    """Try every allowed format twice, then lean on whichever he remembers best. After a 'hard', the plainest format."""
    sp = get(state)
    ok = allowed_formats(sp["level"])
    if sp.get("force_easy"):
        return "phrase" if "phrase" in ok else ok[0], "he found the last one hard, so the plainest format"
    untried = [f for f in ok if _stat(sp, f)["taught"] < 2]
    if untried:
        return untried[0], f"'{untried[0]}' has been tried fewer than 2 times, so learn how it works for him"

    def score(f):
        s = _stat(sp, f)
        tests = s["recall_ok"] + s["recall_fail"]
        return ((s["recall_ok"] + 1) / (tests + 2), -s["hard"])  # smoothed recall rate, then fewer 'hard' answers
    best = max(ok, key=score)
    return best, f"'{best}' has the best recall so far"


def valid_phrase(phrase, level, fmt):
    """Is the Spanish short enough for his level? Dialogue is allowed its two lines."""
    n = len((phrase or "").split())
    return 0 < n <= MAX_WORDS.get(level, 6)


def profile_text(state, today):
    """What Tippy is told, so the AI can decide how to teach him."""
    sp = get(state)
    name, desc = LEVELS[sp["level"]]
    lines = [f"Level {sp['level']} ({name}): {desc} At most {MAX_WORDS[sp['level']]} Spanish words."]
    hist = sp["history"][-6:]
    lines.append("His recent answers (easy / ok / hard): " + (", ".join(f"{h['signal']} [{h['fmt']}, {h['mode']}]" for h in hist) or "none yet"))
    for f in allowed_formats(sp["level"]):
        s = _stat(sp, f)
        lines.append(f"Format {f} ({FORMATS[f]}): taught {s['taught']} times, remembered at review {s['recall_ok']}, forgotten {s['recall_fail']}, "
                     f"found hard {s['hard']}, found easy {s['easy']}.")
    fmt, why = suggest_format(state)
    lines.append(f"Suggested format: {fmt} ({why}). You may pick another allowed format if his answers show it works better; say why in spanish_why.")
    if sp.get("force_easy"):
        lines.append("He found the last item hard. Make this one clearly easier and shorter, and use words he can half-guess from English.")
    lines.append(f"Phrases waiting for review: {sum(1 for b in sp['box'] if b['due'] <= today)}.")
    return "\n".join(lines)


def pick_format(state, wanted):
    sp = get(state)
    wanted = (wanted or "").strip().lower()
    if wanted in allowed_formats(sp["level"]):
        return wanted
    return suggest_format(state)[0]


def mentor_brief(state, mode, fmt, t_out, item=None):
    """The exact Spanish instruction for the Mentor's email. Short on purpose: one item, one small thing to do."""
    if mode == "review" and item:
        return (f"REVIEW day. Ask him to say this once out loud before he looks at the meaning: {item['phrase']} (meaning: {item['english']}; "
                f"first taught on {item['date']}). Then give the meaning in one line. Do not add anything new. "
                "Keep the Spanish exactly as given.")
    say = f" Pronunciation hint for an English speaker: {t_out.get('spanish_say')}." if t_out.get("spanish_say") else ""
    how = {
        "phrase": "Give the phrase, the hint, what it means, and the one moment today to use it.",
        "cognate": "Open with the English word he already knows, show the Spanish twin, then the phrase.",
        "dialogue": "Show it as two short lines, what he says and the answer he is likely to hear.",
        "fill": "Show the sentence with one gap and ask him to say it once with a word of his own.",
    }[fmt]
    return (f"NEW item, format '{fmt}'. {how}{say} Keep the Spanish exactly as given: {t_out.get('spanish_phrase', '')} "
            f"(meaning: {t_out.get('spanish_english', '')}; use: {t_out.get('spanish_when', '')}). "
            "End with one tiny thing to do: say it once out loud at the moment it fits. Three or four lines at most.")


def record_sent(state, today, mode, fmt, t_out, item=None):
    """Remember what he was sent, so his next 'es ...' answer is matched to it."""
    sp = get(state)
    if mode == "review" and item:
        item["due"] = _add_days(today, INTERVALS[min(item["stage"], len(INTERVALS) - 1)])  # if he never answers, it returns later, not tomorrow
        sp["last"] = {"date": today, "mode": "review", "fmt": item["fmt"], "phrase": item["phrase"], "level": sp["level"], "answered": False}
    else:
        phrase = (t_out.get("spanish_phrase") or "").strip()
        if not phrase:
            sp["last"], mode = None, "new"
        else:
            st = _stat(sp, fmt)
            st["taught"] += 1
            if not any(b["phrase"] == phrase for b in sp["box"]):
                sp["box"] = (sp["box"] + [{"phrase": phrase[:120], "english": (t_out.get("spanish_english") or "")[:120], "fmt": fmt,
                                          "date": today, "stage": 0, "due": _add_days(today, INTERVALS[0])}])[-BOX_CAP:]
            sp["last"] = {"date": today, "mode": "new", "fmt": fmt, "phrase": phrase[:120], "level": sp["level"], "answered": False}
    sp["last_mode"] = mode


def summary(state):
    """One line for the weekly memory review: what works for him."""
    sp = get(state)
    parts = [f"level {sp['level']}"]
    for f, s in sp["stats"].items():
        if s["taught"]:
            parts.append(f"{f}: taught {s['taught']}, recalled {s['recall_ok']}, forgot {s['recall_fail']}, hard {s['hard']}")
    return "Spanish coaching: " + "; ".join(parts)
