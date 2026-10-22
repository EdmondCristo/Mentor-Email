"""Run with:  python test_mentor.py   (no API key or email needed)"""
import datetime as dt
import json
import math
import shutil
import tempfile
from pathlib import Path

import mentor


def test_day_numbers():
    assert (dt.date(2026, 10, 19) - mentor.START).days == 1
    assert (dt.date(2027, 1, 10) - mentor.START).days == 84
    assert dt.date(2026, 10, 19).weekday() == 0  # Day 1 is a Monday


def test_phases_and_context():
    assert mentor.phase_for(1) == "Listen First"
    assert mentor.phase_for(28) == "Listen First"
    assert mentor.phase_for(29) == "Bad News Is Welcome"
    assert mentor.phase_for(84) == "Curious by Default"
    assert mentor.phase_for(85) == "Maintenance"
    d1 = mentor.day_context(1, dt.date(2026, 10, 19))
    assert any("investment policy" in s for s in d1["special"])
    sat = mentor.day_context(6, dt.date(2026, 10, 24))
    assert "Saturday" in sat["kind"]
    sun = mentor.day_context(7, dt.date(2026, 10, 25))
    assert "Sunday" in sun["kind"]
    wk4 = mentor.day_context(22, dt.date(2026, 11, 9))
    assert any("Feedback-ask" in s for s in wk4["special"])
    assert mentor.make_subject(d1) == "Day 1 of 84: Listen First"


def test_parse_json():
    assert mentor.parse_json('noise {"a": 1} tail', None) == {"a": 1}
    assert mentor.parse_json("no json", {"x": 0}) == {"x": 0}
    assert mentor.parse_json("{broken", {"x": 0}) == {"x": 0}


def test_short_term_memory_expires_old_entries_and_keeps_pinned_lines():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "m" / "x_short.md"
        p.parent.mkdir()
        p.write_text("# Title\n* pinned seed\n- 2026-10-01 | old entry\n- 2026-10-12 | recent entry\n", encoding="utf-8")
        mentor.append_short(p, "2026-10-19", [f"said {i}" for i in range(80)])
        lines = p.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "# Title" and lines[1] == "* pinned seed"
        assert "old entry" not in "\n".join(lines), "older than 14 days expires"
        assert len(lines) == 2 + mentor.SHORT_CAP and lines[-1].endswith("said 79")


def test_fallback_is_safe_and_nonempty():
    for day, date in [(1, dt.date(2026, 10, 19)), (6, dt.date(2026, 10, 24)), (7, dt.date(2026, 10, 25))]:
        body = mentor.fallback_body(mentor.day_context(day, date))
        assert "Bad-day version" in body


def test_full_mock_run_writes_notebooks():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        shutil.copytree("data", data)
        args = mentor.argparse.Namespace(data_dir=str(data), date="2026-10-19", force=False, mock=True, dry_run=False)
        assert mentor.run(args) == 0
        mem = data / "memory"
        assert "Day 1" in (mem / "mentor_short.md").read_text(encoding="utf-8")
        assert "habit stacking" in (mem / "b_short.md").read_text(encoding="utf-8")
        assert "APPROVE" in (mem / "m_short.md").read_text(encoding="utf-8")
        assert "Offered the" in (mem / "tippy_short.md").read_text(encoding="utf-8")
        assert not (mem / "s_short.md").exists() and not (mem / "s_long.md").exists()
        assert json.loads((data / "state.json").read_text())["last_sent"] == "2026-10-19"
        assert json.loads((data / "state.json").read_text())["last_email"]["lane"] == "qa_skill"
        # B, Tippy and the mentor must never be told about M, in their memory or their memory-keeper prompts
        for name in ("b_short.md", "b_long.md", "tippy_short.md", "tippy_long.md", "mentor_short.md", "mentor_long.md"):
            assert "Agent M" not in (mem / name).read_text(encoding="utf-8"), name


def test_unusable_m_verdict_never_sends_unreviewed_draft():
    original = mentor.agent_m
    mentor.agent_m = lambda *a, **k: None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            shutil.copytree("data", data)
            args = mentor.argparse.Namespace(data_dir=str(data), date="2026-10-19", force=False, mock=True, dry_run=False)
            mentor.run(args)
            assert "BLOCK" in (data / "memory" / "m_short.md").read_text(encoding="utf-8")
    finally:
        mentor.agent_m = original


def test_maintenance_only_on_sundays():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        shutil.copytree("data", data)
        mon = mentor.argparse.Namespace(data_dir=str(data), date="2027-01-11", force=False, mock=True, dry_run=False)
        mentor.run(mon)
        assert (data / "state.json").read_text().strip() == "{}"  # Monday after Day 84: nothing sent
        sun = mentor.argparse.Namespace(data_dir=str(data), date="2027-01-17", force=False, mock=True, dry_run=False)
        mentor.run(sun)
        assert json.loads((data / "state.json").read_text())["last_sent"] == "2027-01-17"


import email.message
import io
import os
import urllib.error


class _FakeResponse:
    def __init__(self, text):
        self._text = text

    def read(self):
        return json.dumps({"choices": [{"message": {"content": self._text}}]}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_error(code, body="boom", retry_after=None):
    headers = email.message.Message()
    if retry_after is not None:
        headers["retry-after"] = str(retry_after)
    return urllib.error.HTTPError("https://api.groq.com", code, "err", headers, io.BytesIO(body.encode()))


def test_groq_is_default_and_request_is_well_formed():
    os.environ.pop("LLM_PROVIDER", None)
    os.environ["GROQ_API_KEY"] = "gsk_test"
    seen = {}

    def fake_urlopen(req, timeout=0):
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        seen["ua"] = req.get_header("User-agent")
        seen["body"] = json.loads(req.data)
        return _FakeResponse('{"advice": "ok"}')

    original = mentor.urllib.request.urlopen
    mentor.urllib.request.urlopen = fake_urlopen
    try:
        llm = mentor.LLM()
        out = llm.ask("[B] sys", "hello", 300, json_mode=True)
    finally:
        mentor.urllib.request.urlopen = original
    assert llm.provider == "groq" and llm.model == mentor.GROQ_PREFERRED[0]
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["auth"] == "Bearer gsk_test" and seen["ua"] == "mentor-email-bot"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert seen["body"]["messages"][0] == {"role": "system", "content": "[B] sys"}
    assert out == '{"advice": "ok"}'


def test_groq_retries_rate_limit_and_drops_json_mode_on_400():
    os.environ["GROQ_API_KEY"] = "gsk_test"
    calls = []

    def flaky(req, timeout=0):
        calls.append(json.loads(req.data))
        if len(calls) == 1:
            raise _http_error(429, retry_after=0)
        if len(calls) == 2:
            raise _http_error(400, "response_format not supported")
        return _FakeResponse("fine")

    original_open, original_sleep = mentor.urllib.request.urlopen, mentor.time.sleep
    mentor.urllib.request.urlopen, mentor.time.sleep = flaky, lambda s: None
    try:
        out = mentor.LLM().ask("[B] sys", "hi", 100, json_mode=True)
    finally:
        mentor.urllib.request.urlopen, mentor.time.sleep = original_open, original_sleep
    assert out == "fine" and len(calls) == 3
    assert "response_format" in calls[0] and "response_format" not in calls[2]


def test_groq_gives_up_with_a_readable_error():
    os.environ["GROQ_API_KEY"] = "bad"

    def always_401(req, timeout=0):
        raise _http_error(401, "invalid api key")

    original = mentor.urllib.request.urlopen
    mentor.urllib.request.urlopen = always_401
    try:
        try:
            mentor.LLM().ask("[B] sys", "hi")
            raise AssertionError("should have raised")
        except RuntimeError as err:
            assert "401" in str(err) and "invalid api key" in str(err)
    finally:
        mentor.urllib.request.urlopen = original


def test_agent_b_never_claims_to_search_when_it_cannot():
    os.environ.pop("B_MODEL", None)
    captured = {}

    class Spy(mentor.LLM):
        def ask(self, system, user, max_tokens=900, web_search=False, json_mode=False):
            captured["system"] = system
            return "{}"

    llm = Spy(mock=True)
    assert llm.can_search is False
    mentor.agent_b(llm, mentor.day_context(1, dt.date(2026, 10, 19)), "plan", "notebook")
    assert "cannot search the web" in captured["system"] and "never invent" in captured["system"]


def test_forced_run_before_start_sends_a_test_and_saves_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        shutil.copytree("data", data)
        before = {str(f.relative_to(data)): f.read_text() for f in data.rglob("*") if f.is_file()}
        sent = []
        original = mentor.send_email
        mentor.send_email = lambda *a: sent.append(a)
        os.environ.update({"GROQ_API_KEY": "k", "GMAIL_ADDRESS": "a@x.com", "GMAIL_APP_PASSWORD": "abcd efgh ijkl mnop", "TO_EMAIL": "b@x.com"})
        os.environ.pop("LLM_PROVIDER", None)
        originals = (mentor.LLM, mentor.fetch_replies)
        mentor.LLM = lambda mock=False: originals[0](mock=True)
        mentor.fetch_replies = lambda *a, **k: []
        try:
            args = mentor.argparse.Namespace(data_dir=str(data), date="2026-10-18", force=True, mock=False, dry_run=False)
            assert mentor.run(args) == 0
            plain = mentor.argparse.Namespace(data_dir=str(data), date="2026-10-18", force=False, mock=False, dry_run=False)
            assert mentor.run(plain) == 0  # not forced: still sends nothing
        finally:
            mentor.send_email, (mentor.LLM, mentor.fetch_replies) = original, originals
        assert len(sent) == 1, "exactly one test email should be sent"
        assert sent[0][3] == "[TEST] Day 1 of 84: Listen First"
        assert sent[0][2] == "b@x.com" and sent[0][1] == "abcdefghijklmnop", "spaces in the app password are removed"
        assert {str(f.relative_to(data)): f.read_text() for f in data.rglob("*") if f.is_file()} == before, "a test must not change any saved file"


def test_groq_404_model_triggers_auto_pick_from_the_models_list():
    os.environ["GROQ_API_KEY"] = "gsk_test"
    os.environ["GROQ_MODEL"] = "llama-3.3-70b-versatile"  # the exact model that failed in the real run
    used = []

    class Raw:
        def __init__(self, payload):
            self.payload = payload

        def read(self):
            return json.dumps(self.payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake(req, timeout=0):
        if req.full_url.endswith("/models"):
            ids = ["whisper-large-v3", "llama-guard-4", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]
            return Raw({"data": [{"id": i} for i in ids]})
        body = json.loads(req.data)
        used.append(body)
        if body["model"] == "llama-3.3-70b-versatile":
            raise _http_error(404, '{"error":{"code":"model_not_found"}}')
        return Raw({"choices": [{"message": {"content": "<think>hmm</think>hello"}}]})

    original = mentor.urllib.request.urlopen
    mentor.urllib.request.urlopen = fake
    try:
        llm = mentor.LLM()
        out = llm.ask("[B] sys", "hi", 400)
        out2 = llm.ask("[B] sys", "again", 400)
    finally:
        mentor.urllib.request.urlopen = original
        os.environ.pop("GROQ_MODEL", None)
    assert out == "hello" and out2 == "hello", "reasoning text must be stripped"
    assert llm.model == "openai/gpt-oss-20b", "skips whisper/guard models, picks the preferred chat model"
    assert [u["model"] for u in used] == ["llama-3.3-70b-versatile", "openai/gpt-oss-20b", "openai/gpt-oss-20b"]
    assert used[1]["reasoning_effort"] == "low" and used[1]["max_tokens"] == 800


RSS = """<?xml version="1.0"?><rss><channel>
<item><title>FDA issues cosmetics   guidance
on labeling</title><link>https://example.com/a</link></item>
<item><title>Recall of lip balm</title><link>https://example.com/b</link></item>
<item><title>No link item</title><link>not-a-url</link></item>
</channel></rss>"""


def _raw_urlopen(routes):
    """Fake urlopen: routes maps a URL substring to the text returned."""
    class Raw:
        def __init__(self, text):
            self.text = text

        def read(self):
            return self.text.encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake(req, timeout=0):
        for key, text in routes.items():
            if key in req.full_url:
                if isinstance(text, Exception):
                    raise text
                return Raw(text)
        raise OSError("unreachable in test")
    return fake


def test_parse_rss_cleans_titles_and_blocks_entity_tricks():
    items = mentor.parse_rss(RSS)
    assert [i["link"] for i in items] == ["https://example.com/a", "https://example.com/b"]
    assert items[0]["title"] == "FDA issues cosmetics guidance on labeling"
    assert mentor.parse_rss(RSS.replace("<rss>", '<!DOCTYPE x [<!ENTITY a "b">]><rss>')) == []
    assert mentor.parse_rss("not xml") == [] and mentor.parse_rss("") == []


def test_weather_line_and_failure_modes():
    ok = json.dumps({"daily": {"weather_code": [61], "temperature_2m_max": [58.4], "temperature_2m_min": [44.1],
                               "precipitation_probability_max": [80]}})
    original = mentor.urllib.request.urlopen
    try:
        mentor.urllib.request.urlopen = _raw_urlopen({"open-meteo": ok})
        line = mentor.get_weather()
        assert "Palisades Park" in line and "rainy" in line and "high 58F" in line and "80%" in line
        mentor.urllib.request.urlopen = _raw_urlopen({"open-meteo": "garbage"})
        assert mentor.get_weather() == ""
        mentor.urllib.request.urlopen = _raw_urlopen({})  # network down
        assert mentor.get_weather() == ""
    finally:
        mentor.urllib.request.urlopen = original


def test_every_weekday_has_a_lane_feeds_angle_and_brief():
    for wd in range(7):
        key, title = mentor.LANES[wd]
        assert key in mentor.LANE_BRIEF and title and wd in mentor.ANGLES
        assert len(mentor.LANE_FEEDS[wd]) >= 2 and all(u.startswith("https://") for _, u in mentor.LANE_FEEDS[wd])
    assert len(set(mentor.SCENARIOS)) == len(mentor.SCENARIOS) == 14


def test_gather_world_skips_used_articles_and_survives_dead_feeds():
    original = mentor.urllib.request.urlopen
    try:
        mentor.urllib.request.urlopen = _raw_urlopen({"news.google.com": RSS, "open-meteo": "x"})
        world = mentor.gather_world(dt.date(2026, 10, 22), used_links=["https://example.com/a"])  # Thursday
        assert [h["link"] for h in world["headlines"]] == ["https://example.com/b"], "used link skipped, duplicates merged"
        assert world["headlines"][0]["n"] == 1
        mentor.urllib.request.urlopen = _raw_urlopen({})
        dead = mentor.gather_world(dt.date(2026, 10, 22), [])
        assert dead == {"weather": "", "headlines": []}
        assert mentor.gather_world(dt.date(2026, 10, 22), [], offline=True)["headlines"] == []
    finally:
        mentor.urllib.request.urlopen = original


def test_repeat_detection_ignores_accents_and_word_order():
    assert mentor.is_repeat("¿Me puede explicar qué vio?", ["me puede explicar que vio"])
    assert mentor.is_repeat("root cause questioning", ["questioning for root cause"])
    assert not mentor.is_repeat("two questions first", ["what would change my mind", "root cause questioning"])
    assert not mentor.is_repeat("", ["anything"])


def test_ledger_round_trip_and_cap():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "u.md"
        p.write_text("# header\n")
        mentor.append_ledger(p, [("2026-10-22", "topic", "root cause | questioning"), ("2026-10-22", "spanish", "Buenos días"),
                                 ("2026-10-22", "topic", "")])
        text = p.read_text()
        assert text.startswith("# header") and "root cause / questioning" in text
        assert mentor.ledger_values(text, "topic") == ["root cause / questioning"]
        assert mentor.ledger_values(text, "spanish") == ["Buenos días"]
        mentor.append_ledger(p, [("2026-10-23", "topic", f"idea {i}") for i in range(200)], cap=50)
        lines = p.read_text().splitlines()
        assert lines[0] == "# header" and len(lines) == 51 and lines[-1].endswith("idea 199")


def test_tippy_is_asked_again_when_it_repeats_itself():
    answers = [
        {"topic": "Root cause", "topic_key": "root cause questioning", "spanish_phrase": "Buenos días"},
        {"topic": "Sampling", "topic_key": "sampling logic", "spanish_phrase": "Muchas gracias"},
    ]
    seen_avoid = []

    class Spy(mentor.LLM):
        def ask(self, system, user, max_tokens=900, web_search=False, json_mode=False):
            seen_avoid.append(user.split("ALSO AVOID right now:")[1].strip())
            return json.dumps(answers[len(seen_avoid) - 1])

    ctx = mentor.day_context(1, dt.date(2026, 10, 19))
    out = mentor.pick_tippy(Spy(mock=True), ctx, "qa_skill", "profile", "", {}, {"weather": "", "headlines": []},
                            ["questioning for root cause"], ["buenos dias"])
    assert out["topic_key"] == "sampling logic" and len(seen_avoid) == 2
    assert "root cause questioning" in seen_avoid[1] and "Buenos días" in seen_avoid[1]
    assert seen_avoid[0] == "[]"


def _run_day(data, date, world, verdict=None, tippy_source_index=1):
    saved = dict(mentor.MOCK)
    mentor.MOCK["TIPPY"] = json.dumps({**json.loads(saved["TIPPY"]), "source_index": tippy_source_index})
    if verdict:
        mentor.MOCK["M"] = json.dumps(verdict)
    original = mentor.gather_world
    mentor.gather_world = lambda *a, **k: world
    try:
        args = mentor.argparse.Namespace(data_dir=str(data), date=date, force=False, mock=True, dry_run=False)
        mentor.run(args)
    finally:
        mentor.gather_world = original
        mentor.MOCK.clear()
        mentor.MOCK.update(saved)


def test_full_day_adds_source_link_and_remembers_what_was_used(capsys=None):
    import contextlib
    world = {"weather": "Palisades Park, NJ today: rainy", "headlines": [{"n": 1, "title": "FDA issues guidance", "link": "https://example.com/a", "feed": "x"}]}
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        shutil.copytree("data", data)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _run_day(data, "2026-10-22", world)
        out = buf.getvalue()
        assert "Source: FDA issues guidance - https://example.com/a" in out, "link is added by code from the feed"
        ledger = (data / "used_topics.md").read_text()
        assert "| topic | what would change my mind" in ledger and "| spanish | ¿Me puede explicar qué vio?" in ledger
        assert json.loads((data / "state.json").read_text())["used_links"] == ["https://example.com/a"]
        assert "what would change my mind" in (data / "memory" / "mentor_short.md").read_text()
        assert "Offered the" in (data / "memory" / "tippy_short.md").read_text()


def test_blocked_day_drops_the_outside_link_and_a_bad_index_is_ignored():
    import contextlib
    world = {"weather": "", "headlines": [{"n": 1, "title": "T", "link": "https://example.com/z", "feed": "x"}]}
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        shutil.copytree("data", data)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _run_day(data, "2026-10-22", world, verdict={"verdict": "BLOCK", "email": "Safe basic note.", "note_to_jason": "",
                                                          "new_checks": [], "log": "blocked"})
        assert "example.com/z" not in buf.getvalue() and "Safe basic note." in buf.getvalue()
        assert json.loads((data / "state.json").read_text()).get("used_links", []) == []
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            _run_day(data, "2026-10-23", world, tippy_source_index=7)
        assert "Source:" not in buf2.getvalue(), "an out-of-range source number must not produce a link"


def test_sensitive_details_never_reach_memory():
    for bad in ["He is 6 ft 1 and 180lb", "his weight is a worry", "height 165", "he mentioned a diagnosis", "my password is abc"]:
        assert mentor.clean_line(bad) == "", bad
    assert mentor.clean_line("Likes short stories | with a pipe") == "Likes short stories / with a pipe"
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "mentor_short.md"
        mentor.append_short(p, "2026-10-19", ["observed: he weighs 180lb", "observed: prefers brief messages"])
        text = p.read_text()
        assert "180" not in text and "prefers brief messages" in text


def test_parse_feedback_reads_ratings_and_ignores_lookalikes():
    assert mentor.parse_feedback("up, loved the Spanish") == (1, "loved the Spanish")
    assert mentor.parse_feedback("👎 too long")[0] == -1
    assert mentor.parse_feedback("Down - too easy") == (-1, "too easy")
    assert mentor.parse_feedback("5/5 great")[0] == 1 and mentor.parse_feedback("2, boring")[0] == -1
    assert mentor.parse_feedback("3")[0] == 0
    for text in ["Update on my day: I listened more", "2 questions were hard today", "Downtown meeting went fine"]:
        assert mentor.parse_feedback(text)[0] is None, text
    assert mentor.parse_feedback("up he weighs 180lb") == (1, "(withheld)")


def test_feedback_lines_link_to_the_email_and_summarize_by_lane():
    last = {"lane": "qa_news", "topic": "label checks"}
    lines = mentor.process_feedback([{"id": "1", "text": "down, too long"}, {"id": "2", "text": "I tried it, felt awkward"}], last, "2026-10-22")
    assert lines[0] == "- 2026-10-22 | lane=qa_news | topic=label checks | score=-1 | note=too long"
    assert "score=none" in lines[1] and "felt awkward" in lines[1]
    more = ["- 2026-10-20 | lane=spanish_talk | topic=x | score=1 | note=", "- 2026-10-21 | lane=spanish_talk | topic=y | score=1 | note="]
    pref, recent = mentor.feedback_summary("\n".join(more + lines))
    assert "spanish_talk: +1.0 (2 rated)" in pref and "qa_news: -1.0 (1 rated)" in pref
    assert recent.count("\n") == 3 and "too long" in recent
    with tempfile.TemporaryDirectory() as tmp:
        mentor.append_feedback(tmp, lines)
        mentor.append_feedback(tmp, more)
        text = (Path(tmp) / "memory" / "feedback.md").read_text()
        assert text.startswith("#") and text.count("\n- ") + 1 == 4 or text.count("- 2026") == 4


def test_old_notebooks_migrate_once_without_overwriting_new_memory():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp)
        (data / "notebook_b.md").write_text("# old\n* seed\n- 2026-10-20: Used habit stacking\n")
        (data / "daylog.md").write_text("# Day log\n- 2026-10-20: Day 2: greeting\n")
        mentor.migrate_old(data)
        assert "habit stacking" in (data / "memory" / "b_long.md").read_text()
        assert "Day 2" in (data / "memory" / "mentor_short.md").read_text()
        (data / "memory" / "b_long.md").write_text("- 2026-10-25: new lesson\n")
        mentor.migrate_old(data)
        assert (data / "memory" / "b_long.md").read_text() == "- 2026-10-25: new lesson\n", "already has entries: leave alone"


def test_memory_block_shows_long_term_then_short_term():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp)
        mentor.write_long(mentor.mem_path(data, "B", "long"), ["Short, concrete advice lands best"], "2026-10-25")
        mentor.remember(data, "B", "2026-10-25", ["advice: pair the greeting with login"])
        block = mentor.memory_block(data, "B")
        assert block.index("LONG-TERM") < block.index("Short, concrete") < block.index("SHORT-TERM") < block.index("pair the greeting")
        assert "(nothing yet)" in mentor.memory_block(data, "M")


def test_weekly_review_rewrites_long_term_but_never_wipes_it():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp)
        path = mentor.mem_path(data, "B", "long")
        path.parent.mkdir(parents=True)
        path.write_text("# header\n* pinned rule\n- 2026-10-18: old lesson\n")
        llm = mentor.LLM(mock=True)
        assert mentor.consolidate(llm, data, "B", "2026-10-25", "") is True
        text = path.read_text()
        assert "# header" in text and "* pinned rule" in text and "old lesson" not in text
        assert "- 2026-10-25: Mock lesson" in text

        class Broken(mentor.LLM):
            def ask(self, *a, **k):
                return "not json"
        before = path.read_text()
        assert mentor.consolidate(Broken(mock=True), data, "B", "2026-11-01", "") is False
        assert path.read_text() == before, "a bad answer must not erase memory"

        class Boom(mentor.LLM):
            def ask(self, *a, **k):
                raise RuntimeError("network")
        mentor.reflect_all(Boom(mock=True), data, "2026-11-01", "")  # must not raise


def test_reflect_prompts_never_mention_m_to_the_other_ais():
    seen = {}

    class Spy(mentor.LLM):
        def ask(self, system, user, *a, **k):
            seen["system"] = system
            return '{"long_term": []}'
    with tempfile.TemporaryDirectory() as tmp:
        for agent in ("B", "TIPPY", "MENTOR"):
            mentor.consolidate(Spy(mock=True), tmp, agent, "2026-10-25", "")
            assert "guardian" not in seen["system"].lower() and "Agent M" not in seen["system"], agent


def test_sunday_run_reviews_memory_once_and_a_weekday_does_not():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        shutil.copytree("data", data)
        for date in ("2026-10-24", "2026-10-25"):  # Saturday, then Sunday
            mentor.run(mentor.argparse.Namespace(data_dir=str(data), date=date, force=False, mock=True, dry_run=False))
            long_b = (data / "memory" / "b_long.md").read_text()
            if date == "2026-10-24":
                assert "Mock lesson" not in long_b and "last_reflect" not in json.loads((data / "state.json").read_text())
        assert "- 2026-10-25: Mock lesson" in long_b
        assert json.loads((data / "state.json").read_text())["last_reflect"] == "2026-10-25"
        mentor.run(mentor.argparse.Namespace(data_dir=str(data), date="2026-10-25", force=False, mock=True, dry_run=False))
        assert (data / "memory" / "b_long.md").read_text().count("Mock lesson") == 1, "reviewed only once a week"


def test_replies_become_feedback_that_shapes_the_next_days_prompts():
    prompts = []

    class Spy(mentor.LLM):
        def ask(self, system, user, *a, **k):
            prompts.append((system.split("]")[0].lstrip("["), user))
            return mentor.MOCK[system.split("]")[0].lstrip("[")]
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        shutil.copytree("data", data)
        orig_llm, orig_fetch = mentor.LLM, mentor.fetch_replies
        os.environ.update({"GROQ_API_KEY": "k", "GMAIL_ADDRESS": "a@x.com", "GMAIL_APP_PASSWORD": "pw", "TO_EMAIL": "b@x.com"})
        os.environ.pop("LLM_PROVIDER", None)
        sent, orig_send = [], mentor.send_email
        mentor.send_email = lambda *a: sent.append(a)
        mentor.LLM = lambda mock=False: Spy(mock=True)
        try:
            mentor.fetch_replies = lambda *a, **k: []
            mentor.run(mentor.argparse.Namespace(data_dir=str(data), date="2026-10-20", force=False, mock=False, dry_run=False))
            assert "[Feedback in 10 seconds" not in sent[0][4] and "Feedback in 10 seconds" in sent[0][4]
            prompts.clear()
            mentor.fetch_replies = lambda *a, **k: [{"id": "m1", "text": "down, the news item was too long"}]
            mentor.run(mentor.argparse.Namespace(data_dir=str(data), date="2026-10-21", force=False, mock=False, dry_run=False))
        finally:
            mentor.LLM, mentor.fetch_replies, mentor.send_email = orig_llm, orig_fetch, orig_send
        fb = (data / "memory" / "feedback.md").read_text()
        assert "lane=spanish_work" in fb or "lane=qa_skill" in fb
        assert "score=-1 | note=the news item was too long" in fb
        by_agent = dict(prompts)
        for agent in ("TIPPY", "MENTOR"):
            assert "too long" in by_agent[agent], f"{agent} should see his feedback"
        assert "too long" in by_agent["TIPPY"] and "-1.0 (1 rated)" in by_agent["TIPPY"]


import email
import types


def _mail(frm, subject, body, mid, extra=None):
    m = email.message.EmailMessage()
    m["From"], m["To"], m["Subject"], m["Message-ID"] = frm, "bot@x.com", subject, mid
    for k, v in (extra or {}).items():
        m[k] = v
    m.set_content(body)
    return m.as_bytes()


class FakeIMAP:
    mailbox = []

    def __init__(self, host):
        pass

    def login(self, user, password):
        pass

    def select(self, name, readonly=True):
        return ("OK", [b"1"])

    def search(self, charset, *criteria):
        sender = criteria[-1].strip('"').lower()
        hits = [str(i).encode() for i, raw in enumerate(FakeIMAP.mailbox)
                if sender in email.message_from_bytes(raw).get("From", "").lower()]
        return ("OK", [b" ".join(hits)])

    def fetch(self, num, spec):
        return ("OK", [(b"", FakeIMAP.mailbox[int(num)])])

    def logout(self):
        pass


def test_mailbox_reads_any_subject_and_skips_own_mail_strangers_and_forgeries():
    me = "jason@x.com"
    FakeIMAP.mailbox = [
        _mail(me, "Hello team", "I want more Spanish practice.", "<a1>"),
        _mail(me, "Re: Day 3 of 84: Listen First", "up, loved it\n\nOn Wed, Oct 21 wrote:\n> quoted text", "<b1>"),
        _mail(me, "Day 3 of 84: Listen First", "the bot's own email to itself", "<c1>", {"X-Mentor-Bot": "1"}),
        _mail("notjason@x.com", "Hi", "someone with a similar address", "<d1>"),
        _mail(me, "Re: Day 3", "forged", "<e1>", {"Authentication-Results": "mx.google.com; dkim=fail; spf=pass"}),
        _mail(me, "Old news", "already handled", "<f1>"),
        _mail(me, "=?utf-8?q?Pregunta_para_S?=", "Una pregunta", "<g1>"),
    ]
    original = mentor.imaplib.IMAP4_SSL
    mentor.imaplib.IMAP4_SSL = FakeIMAP
    try:
        got = mentor.read_mailbox("bot@x.com", "pw", [me], seen=["<f1>"])
    finally:
        mentor.imaplib.IMAP4_SSL = original
    by_id = {m["id"]: m for m in got}
    assert sorted(by_id) == ["<a1>", "<b1>", "<g1>"], "bot's own mail, strangers, forgeries and seen mail are skipped"
    assert by_id["<a1>"]["kind"] == "direct" and by_id["<b1>"]["kind"] == "reply"
    assert by_id["<b1>"]["text"] == "up, loved it", "quoted history is cut"
    assert by_id["<g1>"]["subject"] == "Pregunta para S"


def test_allowed_senders_come_from_your_address_plus_the_optional_list():
    os.environ.pop("ALLOWED_SENDERS", None)
    assert mentor.allowed_senders(" Jason@X.com ") == ["jason@x.com"]
    os.environ["ALLOWED_SENDERS"] = "mom@x.com, Jason@x.com"
    try:
        assert mentor.allowed_senders("jason@x.com") == ["jason@x.com", "mom@x.com"]
    finally:
        os.environ.pop("ALLOWED_SENDERS")


def test_direct_messages_are_not_ratings():
    lines = mentor.process_feedback([{"id": "1", "kind": "direct", "text": "up the pace please"},
                                     {"id": "2", "kind": "reply", "text": "up, nice"}], {"lane": "qa_skill", "topic": "t"}, "2026-10-22")
    assert len(lines) == 1 and "score=1" in lines[0]


def _fresh_data(tmp):
    data = Path(tmp) / "data"
    shutil.copytree("data", data)
    return data


def test_every_email_the_bot_sends_is_stamped_so_it_never_reads_its_own_mail():
    class FakeSMTP:
        sent = []

        def __init__(self, host, port):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, user, password):
            pass

        def send_message(self, msg):
            FakeSMTP.sent.append(msg)

    original = mentor.smtplib.SMTP_SSL
    mentor.smtplib.SMTP_SSL = FakeSMTP
    try:
        mentor.send_email("bot@x.com", "pw", "jason@x.com", "Day 1", "hi")
    finally:
        mentor.smtplib.SMTP_SSL = original
    assert FakeSMTP.sent[0]["X-Mentor-Bot"] == "1" and FakeSMTP.sent[0]["From"] == "Your Mentor <bot@x.com>"


def test_direct_email_goes_to_the_mentor_and_nobody_writes_back():
    os.environ.update({"GROQ_API_KEY": "k", "GMAIL_ADDRESS": "bot@x.com", "GMAIL_APP_PASSWORD": "pw", "TO_EMAIL": "jason@x.com"})
    os.environ.pop("LLM_PROVIDER", None)
    prompts, sent = [], []

    class Spy(mentor.LLM):
        def ask(self, system, user, *a, **k):
            tag = system.split("]")[0].lstrip("[")
            prompts.append((tag, system, user))
            return mentor.MOCK[tag]

    mail = [{"id": "<d1>", "kind": "direct", "subject": "Hello", "text": "Please keep the emails short. I weigh 180lb."},
            {"id": "<r1>", "kind": "reply", "subject": "Re: Day 1 of 84", "text": "up, nice"}]
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        shutil.copytree("data", data)
        saved = (mentor.LLM, mentor.fetch_replies, mentor.send_email, mentor.gather_world)
        mentor.LLM = lambda mock=False: Spy(mock=True)
        mentor.fetch_replies = lambda *a, **k: list(mail)
        mentor.send_email = lambda *a, **k: sent.append((a, k))
        mentor.gather_world = lambda *a, **k: {"weather": "", "headlines": []}
        try:
            mentor.run(mentor.argparse.Namespace(data_dir=str(data), date="2026-10-20", force=False, mock=False, dry_run=False))
        finally:
            mentor.LLM, mentor.fetch_replies, mentor.send_email, mentor.gather_world = saved
        assert len(sent) == 1, "only the daily email goes out"
        assert "is read by the Mentor, who uses it to tune your emails but does not write back" in sent[0][0][4]
        assert "Confirmed by M: I received 2 emails from you." in sent[0][0][4]
        assert 'Your email "Hello": read by the Mentor; a private detail was left out of memory.' in sent[0][0][4]
        assert 'Your reply "up, nice": counted as feedback.' in sent[0][0][4]
        tags = {p[0] for p in prompts}
        assert "S" not in tags and {"B", "TIPPY", "MENTOR", "M"} <= tags
        mentor_user = [p for p in prompts if p[0] == "MENTOR"][0][2]
        assert "[direct email to the team, subject: Hello]" in mentor_user and "up, nice" not in mentor_user.split("his emails to you")[1]
        short = (data / "memory" / "mentor_short.md").read_text()
        assert "180" not in short, "sensitive details are never remembered"
        assert set(json.loads((data / "state.json").read_text())["seen_ids"]) == {"<d1>", "<r1>"}
        fb = (data / "memory" / "feedback.md").read_text()
        assert fb.count("score=1") == 1 and "emails short" not in fb, "only the reply is a rating"


def test_m_confirms_each_email_and_stays_silent_when_there_is_none():
    assert mentor.m_receipt([]) == ""
    one = mentor.m_receipt([{"kind": "direct", "subject": "Idea", "text": "More soccer examples please"}])
    assert one == 'Confirmed by M: I received 1 email from you.\n- Your email "Idea": read by the Mentor and noted.'
    many = mentor.m_receipt([{"kind": "reply", "subject": "Re: x", "text": f"up {i}"} for i in range(8)])
    assert "received 8 emails" in many and "...and 2 more." in many


def test_vividness_scores_senses_places_and_metaphor():
    scene = "She walked past the bakery, the door creaked, cinnamon hit her. It felt like stepping into a warm hug."
    assert mp.rate_vividness(scene) == 10, "3 senses (5+2+2) + place + metaphor, capped at 10"
    assert mp.rate_vividness("The door creaked and cinnamon hit her") == 7, "two senses"
    assert mp.rate_vividness("I heard a loud noise in the hall") == 5, "one sense"
    assert mp.rate_vividness("the meeting was at 3 on the schedule") == 2, "flat, abstract"
    assert mp.rate_vividness("I went to the store") == 2 and mp.rate_vividness("ok then") == 1
    assert mp.rate_vividness("Basically I heard a loud noise anyway") == 3, "flat words subtract 2"
    five = "The room smelled like coffee, I could feel the cold on my skin, the sound of rain, the light was gold, it tasted of smoke"
    assert mp.rate_vividness(five) == 10
    assert len(mp.rate_statement(five)["cues"]) <= 8


def test_cues_let_one_keyword_revive_a_vivid_memory():
    story = ("Long ago I was on a quiet street with a thousand small worries and a lot of other things going on, and then "
             "she walked past the bakery, the door creaked, cinnamon hit her and I remember the exact moment everything became gold. " * 2)
    r = mp.rate_statement(story)
    assert r["vividness"] >= 8 and 3 <= len(r["cues"]) <= 8 and any(c.endswith(":cinnamon") for c in r["cues"])
    assert len({c.split(":", 1)[1] for c in r["cues"]}) == len(r["cues"]), "one cue per word"
    store = mp.empty_store()
    now = dt.datetime(2026, 10, 20, 8, 0)
    rec = mp.add(store, "MENTOR", "x" * 10 + " a long story that was cut short", 3, [], "EPISODIC", now, "jason", r["vividness"], r["cues"])
    mp.add(store, "MENTOR", "unrelated chat about invoices", 3, [], "EPISODIC", now, "jason")
    got = mp.retrieve(store, "I bought a cinnamon latte", now, minimum=1, limit=1)
    assert got[0]["id"] == rec["id"], "cinnamon matches a cue even though the saved summary does not say it"
    assert mp.retrieve(store, "payroll", now, minimum=0, limit=5) == []


def test_vivid_memories_are_protected_from_forgetting():
    now = dt.datetime(2027, 3, 1, 7, 0)
    store = mp.empty_store()
    store["memories"] = [_mem("flat and forgettable", 3, viv=2), _mem("a vivid scene", 3, viv=5),
                         _mem("a very vivid scene", 2, viv=9), _mem("intense", 9.5, viv=1)]
    assert mp.forget(store, now) == 1
    assert {m["text"] for m in store["memories"]} == {"a vivid scene", "a very vivid scene", "intense"}


def test_unused_vivid_memory_gets_a_sensory_hook_after_seven_days():
    store = mp.empty_store()
    store["memories"] = [_mem("tired, but the door creaked and cinnamon hit her as she walked past the bakery", 4, viv=9, last="2026-10-01T08:00"),
                         _mem("a vivid but recent scene", 4, viv=9, last="2026-10-18T08:00"),
                         _mem("flat note", 4, viv=2, last="2026-10-01T08:00")]
    s = mp.session_summary(store, "2026-10-20", [], dt.datetime(2026, 10, 20, 8, 0))
    assert s["hooks"] == ["cinnamon hit her as she walked past the bakery"] and "sensory hook" in s["line"]
    assert "cinnamon" in mp.render([], store, dt.datetime(2026, 10, 20, 8, 0))
    again = mp.session_summary(store, "2026-10-21", [], dt.datetime(2026, 10, 21, 8, 0))
    assert again["hooks"] == [], "a memory is only hooked once"


def test_three_send_windows_in_eastern_time():
    def at(h, m):
        return dt.datetime(2026, 10, 21, h, m)
    assert [mentor.slot_now(at(h, m)) for h, m in ((7, 59), (8, 0), (12, 59), (13, 0), (15, 59), (16, 0), (20, 59), (21, 0))] == \
        [None, "morning", "morning", "midday", "midday", "afternoon", "afternoon", None]
    assert mentor.SLOT_NAMES == {"morning": "8:00 a.m.", "midday": "1:00 p.m.", "afternoon": "4:00 p.m."}
    wf = Path(".github/workflows/daily-mentor.yml").read_text()
    for utc in ("12", "13", "17", "18", "20", "21"):  # 8:00, 1:00 pm and 4:00 pm Eastern in summer and winter time
        assert utc in wf.split("cron:")[1].split("\n")[0]
    ctx = mentor.day_context(3, dt.date(2026, 10, 21))
    assert [mentor.slot_subject(ctx, s) for s in ("morning", "midday", "afternoon")] == \
        ["Day 3 of 84: Listen First", "Day 3: midday check-in", "Day 3: 4 PM reflection"]


def test_three_emails_a_day_with_short_followups_that_skip_b_and_tippy():
    os.environ.update({"GROQ_API_KEY": "k", "GMAIL_ADDRESS": "bot@x.com", "GMAIL_APP_PASSWORD": "pw", "TO_EMAIL": "jason@x.com"})
    os.environ.pop("LLM_PROVIDER", None)
    prompts, sent = [], []

    class Spy(mentor.LLM):
        def ask(self, system, user, *a, **k):
            tag = system.split("]")[0].lstrip("[")
            prompts.append((tag, system, user))
            return mentor.MOCK[tag]

    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        shutil.copytree("data", data)
        saved = (mentor.LLM, mentor.fetch_replies, mentor.send_email, mentor.gather_world)
        mentor.LLM = lambda mock=False: Spy(mock=True)
        mentor.fetch_replies = lambda *a, **k: []
        mentor.send_email = lambda *a, **k: sent.append(a[3:])
        mentor.gather_world = lambda *a, **k: {"weather": "", "headlines": []}

        def go(slot, date="2026-10-20", **kw):
            return mentor.run(mentor.argparse.Namespace(data_dir=str(data), date=date, force=False, mock=False, dry_run=False, slot=slot, **kw))
        try:
            go("midday")  # nothing sent this morning yet: the run sends the morning email first
            assert sent[0][0] == "Day 2 of 84: Listen First"
            n = len(prompts)
            go("midday")
            go("afternoon")
        finally:
            mentor.LLM, mentor.fetch_replies, mentor.send_email, mentor.gather_world = saved
        assert [s[0] for s in sent] == ["Day 2 of 84: Listen First", "Day 2: midday check-in", "Day 2: 4 PM reflection"]
        later = [p[0] for p in prompts[n:]]
        assert "B" not in later and "TIPPY" not in later, "follow-ups only use the Mentor and Agent M"
        assert later.count("MENTOR") == 2 and later.count("M") == 2
        mid = [p for p in prompts[n:] if p[0] == "MENTOR"][0]
        assert "MIDDAY check-in" in mid[1] and "This morning's email (do not repeat it)" in mid[2] and "Today's practice" in mid[2]
        assert "4 PM end-of-workday reflection" in [p for p in prompts[n:] if p[0] == "MENTOR"][1][1]
        state = json.loads((data / "state.json").read_text())
        assert state["slots"] == {"date": "2026-10-20", "done": ["afternoon", "midday", "morning"]}
        assert state["last_sent"] == "2026-10-20" and state["today"]["date"] == "2026-10-20" and "(Feedback" not in state["today"]["body"]
        assert mentor.sent_today(state, "2026-10-20") == {"morning", "midday", "afternoon"}
        assert mentor.sent_today(state, "2026-10-21") == set()
        assert "midday" in (data / "memory" / "mentor_short.md").read_text()


def test_mission_file_matches_the_built_in_text_and_can_be_edited():
    assert Path("data/mission.md").read_text(encoding="utf-8") == mentor.MISSION
    with tempfile.TemporaryDirectory() as tmp:
        assert mentor.load_mission(tmp) == mentor.MISSION, "no file: the built-in mission is used"
        (Path(tmp) / "mission.md").write_text("MY OWN MISSION\n", encoding="utf-8")
        assert mentor.load_mission(tmp) == "MY OWN MISSION\n"
    for word in ("one-push-up", "FLOOR", "under 30 seconds", "7 \"done\" days in a row", "No quotes, slogans", "QA", "wife", "parents", "Mondays"):
        assert word in mentor.MISSION, word
    assert "Agent M" not in mentor.MISSION and "guardian" not in mentor.MISSION.lower()


def test_every_ai_gets_the_mission_but_only_m_gets_the_mission_checks():
    os.environ.update({"GROQ_API_KEY": "k", "GMAIL_ADDRESS": "bot@x.com", "GMAIL_APP_PASSWORD": "pw", "TO_EMAIL": "jason@x.com"})
    os.environ.pop("LLM_PROVIDER", None)
    prompts = []

    class Spy(mentor.LLM):
        def ask(self, system, user, *a, **k):
            tag = system.split("]")[0].lstrip("[")
            prompts.append((tag, system, user))
            return mentor.MOCK[tag]

    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        shutil.copytree("data", data)
        saved = (mentor.LLM, mentor.fetch_replies, mentor.send_email, mentor.gather_world)
        mentor.LLM = lambda mock=False: Spy(mock=True)
        mentor.fetch_replies = lambda *a, **k: []
        mentor.send_email = lambda *a, **k: None
        mentor.gather_world = lambda *a, **k: {"weather": "", "headlines": []}
        try:
            for date, slot in (("2026-10-25", "morning"), ("2026-10-25", "midday")):  # a Sunday: reflection runs too
                mentor.run(mentor.argparse.Namespace(data_dir=str(data), date=date, force=False, mock=False, dry_run=False, slot=slot))
        finally:
            mentor.LLM, mentor.fetch_replies, mentor.send_email, mentor.gather_world = saved
    tags = [p[0] for p in prompts]
    assert {"B", "TIPPY", "MENTOR", "M", "REFLECT"} <= set(tags)
    for tag, system, user in prompts:
        assert "MISSION (everything you do serves this)" in system and "one-push-up" in system, tag
        assert ("YOUR CHECKS ON THE MISSION" in system) == (tag == "M"), tag
        if tag in ("B", "TIPPY", "MENTOR"):
            assert "Agent M" not in system and "guardian" not in system.lower(), f"{tag} must not learn about M"
    mentor_morning = [p for p in prompts if p[0] == "MENTOR"][0]
    assert "Tiny promise (life)" in mentor_morning[1] and "Mission area today: life" in mentor_morning[2], "Sunday is a life day"
    assert "Level 1: today's promise may take up to 30 seconds" in mentor_morning[2]
    assert "15. The 8:00 email carries exactly one tiny promise" in [p for p in prompts if p[0] == "M"][0][2]


def test_area_rotation_covers_all_four_areas_across_the_week():
    assert [mentor.MISSION_AREAS[d] for d in range(7)] == ["life", "job", "love", "family", "love", "family", "life"]
    assert set(mentor.MISSION_AREAS.values()) == {"job", "love", "family", "life"}


def test_reply_words_for_the_tiny_promise():
    assert [mentor.parse_promise(t) for t in ("done", "Done, easy", "floor - only the short one", "skip", "Skipped it", "missed", "up, nice", "donut", "undone", "")] == \
        ["done", "done", "floor", "skip", "skip", "skip", None, None, None, None]


def test_ladder_steps_up_after_seven_done_days_and_shrinks_after_a_skip():
    state = {}
    mentor.open_promise(state, "2026-10-20", "job", "After login, greet one inspector")
    say = lambda word: mentor.apply_promise_results(state, [{"kind": "reply", "text": word}])
    say("floor")
    assert state["ladder"] == {"level": 1, "run": 0, "floor_next": False}, "floor keeps the promise but does not count toward stepping up"
    for i in range(6):
        mentor.open_promise(state, f"2026-10-2{i + 1}", "job", "x")
        say("done")
    assert state["ladder"]["run"] == 6 and state["ladder"]["level"] == 1
    mentor.open_promise(state, "2026-10-27", "love", "y")
    say("done now")
    assert state["ladder"]["level"] == 2 and state["ladder"]["run"] == 0, "seven in a row: one step up, never double"
    assert "up to 2 minutes" in mentor.ladder_note(state)
    mentor.open_promise(state, "2026-10-28", "family", "z")
    say("skip")
    assert state["ladder"]["run"] == 0 and state["ladder"]["floor_next"] is True and state["ladder"]["level"] == 2
    assert "WHOLE promise today must be the floor version" in mentor.ladder_note(state)
    mentor.open_promise(state, "2026-10-29", "life", "w")
    assert state["ladder"]["floor_next"] is False, "the floor-only day is issued once"
    mentor.open_promise(state, "2026-10-30", "life", "v")  # yesterday's promise never got an answer
    assert state["promises"][-1]["result"] == "no reply" and state["ladder"]["level"] == 2
    say("done")  # an answer with no promise open, or a rating, changes nothing
    say("done")
    assert state["ladder"]["run"] == 1
    mentor.apply_promise_results(state, [{"kind": "direct", "text": "done"}, {"kind": "reply", "text": "up"}])
    assert state["ladder"]["run"] == 1, "only replies to the daily email count, and ratings are not answers"


def test_promise_is_tracked_end_to_end_and_confirmed_by_m():
    os.environ.update({"GROQ_API_KEY": "k", "GMAIL_ADDRESS": "bot@x.com", "GMAIL_APP_PASSWORD": "pw", "TO_EMAIL": "jason@x.com"})
    os.environ.pop("LLM_PROVIDER", None)
    sent, prompts = [], []

    class Spy(mentor.LLM):
        def ask(self, system, user, *a, **k):
            tag = system.split("]")[0].lstrip("[")
            prompts.append((tag, system, user))
            if tag == "MENTOR" and "Tiny promise" in system and "MIDDAY" not in system and "4 PM" not in system:
                return ("Tiny promise (job): After I log in, I will greet one inspector in Spanish.\nFloor version: say Buenos dias.\n"
                        "Why: a tiny habit tied to a habit sticks.\n\nTonight's question: Who did you greet?\n\nLOG: greeting | angle | none | q")
            return mentor.MOCK[tag]

    mail = {"2026-10-21": [{"id": "<1>", "kind": "reply", "subject": "Re: Day 2", "text": "done, easy"}]}
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        shutil.copytree("data", data)
        saved = (mentor.LLM, mentor.fetch_replies, mentor.send_email, mentor.gather_world)
        mentor.LLM = lambda mock=False: Spy(mock=True)
        mentor.send_email = lambda *a, **k: sent.append(a[3:])
        mentor.gather_world = lambda *a, **k: {"weather": "", "headlines": []}
        try:
            for date in ("2026-10-20", "2026-10-21"):
                mentor.fetch_replies = lambda *a, date=date, **k: list(mail.get(date, []))
                mentor.run(mentor.argparse.Namespace(data_dir=str(data), date=date, force=False, mock=False, dry_run=False, slot="morning"))
        finally:
            mentor.LLM, mentor.fetch_replies, mentor.send_email, mentor.gather_world = saved
        state = json.loads((data / "state.json").read_text())
        assert state["promises"][0] == {"date": "2026-10-20", "area": "job", "text": "After I log in, I will greet one inspector in Spanish.",
                                        "level": 1, "result": "done"}
        assert state["ladder"]["run"] == 1 and state["promise_open"]["date"] == "2026-10-21" and state["promise_open"]["area"] == "love"
        assert "Tiny promise: reply 'done', 'floor'" in sent[0][1]
        assert 'noted as your tiny promise result (done)' in sent[1][1]
        day2 = [p for p in prompts if p[0] == "MENTOR"][-1]
        assert "Mission area today: love" in day2[2] and "'Done' days in a row at this level: 1 of 7" in day2[2]


def test_agent_s_is_gone():
    import inspect
    assert not hasattr(mentor, "agent_s") and "S" not in mentor.AGENTS and "S" not in mentor.MOCK
    assert not Path(".github/workflows/agent-s-inbox.yml").exists()
    assert not list(Path("data/memory").glob("s_*.md"))
    assert "Agent S" not in inspect.getsource(mentor)


import memory_protocol as mp


def _mem(text="x", sal=5.0, tags=(), typ="EPISODIC", created="2026-10-01T07:00", last=None, count=0, viv=1.0, cues=()):
    return {"id": text[:8] + str(sal), "text": text, "salience": sal, "tags": list(tags), "type": typ,
            "vividness": viv, "cues": list(cues),
            "created": created, "last_access": last or created, "access_count": count, "source": "t"}


def test_salience_follows_the_vocabulary_guide():
    r = mp.rate_statement("I was terrified of the audit")
    assert (r["salience"], r["tags"]) == (7, ["fear"])
    r = mp.rate_statement("I am overjoyed and proud of the team")
    assert r["salience"] == 7 and r["tags"] == ["joy", "pride"]
    assert mp.rate_statement("whatever, fine")["salience"] == 1, "flat words lower it, floor 1"
    assert mp.rate_statement("up, nice")["salience"] == 2, "a bare rating is routine"
    assert mp.rate_statement("The schedule is okay for now, I guess")["salience"] == 2
    assert mp.rate_statement("I fine-tuned the model today")["salience"] == 4, "'fine-tuned' is not the word 'fine'"
    assert mp.rate_statement("I'm so relieved it passed")["tags"] == ["relief"]
    assert mp.rate_statement("I really love short emails")["type"] == "SEMANTIC"
    assert mp.rate_statement("I always skip the greeting")["type"] == "PROCEDURAL"
    assert mp.rate_statement("Met Nancy at lunch")["type"] == "EPISODIC"


def test_effective_weight_formula_and_flashbulb_floor():
    now = dt.datetime(2026, 10, 3, 7, 0)
    m = _mem(sal=8, viv=4, last="2026-10-01T07:00", count=3)  # 48 hours old
    assert abs(mp.effective_weight(m, now) - (8 * 0.6 + 4 * 0.4) * 0.95 ** 2 * (1 + 0.1 * math.log(4))) < 1e-6
    old = _mem(sal=9, viv=1, last="2025-01-01T07:00")
    assert abs(mp.effective_weight(old, now) - (9 * 0.6 + 1 * 0.4) * 0.5) < 1e-6, "salience 9 never fades below half"
    vivid = _mem(sal=3, viv=8, last="2025-01-01T07:00")
    assert abs(mp.effective_weight(vivid, now) - (3 * 0.6 + 8 * 0.4) * 0.6) < 1e-6, "vividness 8 keeps decay at 0.6 or more"
    both = _mem(sal=9, viv=9, last="2025-01-01T07:00")
    assert abs(mp.effective_weight(both, now) - (9 * 0.6 + 9 * 0.4) * 0.6) < 1e-6, "the higher floor applies"
    assert mp.effective_weight(_mem(sal=8, viv=7, last="2025-01-01T07:00"), now) < 0.01


def test_retrieval_prefers_similar_then_mood_then_weight_and_pads_to_three():
    now = dt.datetime(2026, 10, 20, 7, 0)
    store = mp.empty_store()
    store["memories"] = [_mem("spanish greeting with inspectors", 4, last="2026-10-19T07:00"),
                         _mem("terrified of the audit", 7, ["fear"], last="2026-10-19T07:00"),
                         _mem("proud of the team", 8, ["pride"], last="2026-10-19T07:00"),
                         _mem("unrelated soccer match", 9, ["joy"], last="2026-10-19T07:00")]
    got = mp.retrieve(store, "practice a spanish greeting and the audit", now, mood_tags={"fear"}, limit=5)
    assert [m["text"] for m in got] == ["terrified of the audit", "unrelated soccer match", "spanish greeting with inspectors"], \
        "mood match first, then by weight; two matches were padded to three with the strongest other memory"
    assert "proud of the team" not in [m["text"] for m in got], "no match and not strong enough to pad"
    calm = mp.retrieve(store, "practice a spanish greeting and the audit", now)
    assert calm[0]["text"] == "unrelated soccer match", "without a mood, the heaviest memory leads"
    assert len(mp.retrieve(store, "audit", now, minimum=1, limit=1)) == 1
    assert mp.retrieve(mp.empty_store(), "anything", now) == []


def test_recalled_memories_come_back_stronger_up_to_ten():
    now = dt.datetime(2026, 10, 20, 7, 0)
    m = _mem(sal=9.9)
    mp.reconsolidate([m], now)
    assert m["salience"] == 10.0 and m["access_count"] == 1 and m["last_access"] == "2026-10-20T07:00"
    n = _mem(sal=3)
    mp.reconsolidate([n], now)
    assert n["salience"] == 3.25


def test_forgetting_drops_faded_low_salience_but_never_high_salience():
    now = dt.datetime(2026, 12, 1, 7, 0)  # 61 days after the memories were last used
    store = mp.empty_store()
    store["memories"] = [_mem("neutral fact", 2), _mem("mild interest", 3.5), _mem("meaningful", 5),
                         _mem("deep", 9), _mem("fresh neutral", 2, last="2026-11-30T07:00")]
    assert mp.forget(store, now) == 2
    assert {m["text"] for m in store["memories"]} == {"meaningful", "deep", "fresh neutral"}
    # by the protocol's own formula a never-used salience-1 memory falls under 0.3 after about 24 days (the fourth weekly pass)
    one = mp.empty_store(); one["memories"] = [_mem("trivia", 1, last="2026-10-01T07:00")]
    assert mp.forget(one, dt.datetime(2026, 10, 15, 7, 0)) == 0
    assert mp.forget(one, dt.datetime(2026, 10, 22, 7, 0)) == 0
    assert mp.forget(one, dt.datetime(2026, 10, 29, 7, 0)) == 1


def test_consolidation_merges_resolves_contradictions_and_promotes():
    now = dt.datetime(2026, 10, 25, 7, 0)
    store = mp.empty_store()
    store["memories"] = [_mem("he said: keep the emails short", 4, created="2026-10-19T07:00", last="2026-10-24T07:00"),
                         _mem("he said: keep the emails short", 6, ["relief"], created="2026-10-22T07:00", last="2026-10-24T07:00", count=1)]
    store["memories"][1]["id"] = "other"
    assert mp.merge_related(store) == 1 and len(store["memories"]) == 1
    kept = store["memories"][0]
    assert kept["salience"] == 6 and kept["access_count"] == 1 and kept["tags"] == ["relief"]
    # contradictions: newer wins unless the older one is more salient
    s2 = mp.empty_store()
    s2["memories"] = [_mem("likes long emails", 4, created="2026-10-19T07:00") | {"id": "old"},
                      _mem("likes short emails", 5, created="2026-10-22T07:00") | {"id": "new"}]
    assert mp.resolve_contradictions(s2, [["old", "new"]]) == 1 and [m["id"] for m in s2["memories"]] == ["new"]
    s3 = mp.empty_store()
    s3["memories"] = [_mem("a", 8, created="2026-10-19T07:00") | {"id": "old"}, _mem("b", 4, created="2026-10-22T07:00") | {"id": "new"}]
    mp.resolve_contradictions(s3, [["new", "old"], ["old", "ghost"], ["old", "old"]])
    assert [m["id"] for m in s3["memories"]] == ["old"], "a more salient older memory survives; bad pairs are ignored"
    # promotion
    s4 = mp.empty_store()
    s4["memories"] = [_mem("he loves short stories", 8), _mem("a big surprise at the audit", 8), _mem("he loves tea", 5)]
    assert mp.promote(s4) == 1 and s4["memories"][0]["type"] == "SEMANTIC" and s4["memories"][1]["type"] == "EPISODIC"
    s4["memories"][1]["access_count"] = 2
    assert mp.promote(s4) == 1


def test_session_summary_names_the_dominant_feeling():
    store = mp.empty_store()
    new = [_mem("he was terrified", 7, ["fear"]), _mem("he was proud", 7, ["pride"]), _mem("scared again", 8, ["fear"])]
    s = mp.session_summary(store, "2026-10-20", new)
    assert s["tag"] == "fear" and "3 new memories" in s["line"]
    assert mp.session_summary(store, "2026-10-21", [_mem("routine", 2)])["tag"] == "neutral"
    mp.session_summary(store, "2026-10-21", [])
    assert len(store["sessions"]) == 2, "one summary per day"


def test_every_ai_keeps_an_emotional_store_and_recalls_it_the_next_day():
    os.environ.update({"GROQ_API_KEY": "k", "GMAIL_ADDRESS": "bot@x.com", "GMAIL_APP_PASSWORD": "pw", "TO_EMAIL": "jason@x.com"})
    os.environ.pop("LLM_PROVIDER", None)
    prompts = []

    class Spy(mentor.LLM):
        def ask(self, system, user, *a, **k):
            tag = system.split("]")[0].lstrip("[")
            prompts.append((tag, system, user))
            return mentor.MOCK[tag]

    day1 = [{"id": "<1>", "kind": "direct", "subject": "audit", "text": "I was terrified of the audit but proud we passed."},
            {"id": "<2>", "kind": "direct", "subject": "x", "text": "I weigh 180lb and I am devastated."}]
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        shutil.copytree("data", data)
        saved = (mentor.LLM, mentor.fetch_replies, mentor.send_email, mentor.gather_world)
        mentor.LLM = lambda mock=False: Spy(mock=True)
        mentor.send_email = lambda *a, **k: None
        mentor.gather_world = lambda *a, **k: {"weather": "", "headlines": []}
        try:
            for date, mail in (("2026-10-20", day1), ("2026-10-21", [])):
                if date == "2026-10-21":
                    day2_start = len(prompts)
                mentor.fetch_replies = lambda *a, mail=mail, **k: list(mail)
                mentor.run(mentor.argparse.Namespace(data_dir=str(data), date=date, force=False, mock=False, dry_run=False))
        finally:
            mentor.LLM, mentor.fetch_replies, mentor.send_email, mentor.gather_world = saved
        for agent in ("b", "tippy", "mentor", "m"):
            store = mp.load(data / "memory" / f"{agent}_store.json")
            texts = " ".join(m["text"] for m in store["memories"])
            assert "terrified" in texts and "180" not in texts and "devastated" not in texts, "sensitive mail is never stored"
            mem = [m for m in store["memories"] if "terrified" in m["text"]][0]
            assert mem["tags"] == ["fear", "pride"] and mem["type"] == "EPISODIC"
            assert (mem["salience"], mem["access_count"]) == (7.25, 1), f"{agent} recalled it once on day 2 and it came back stronger"
            assert len(store["sessions"]) == 2 and store["sessions"][0]["tag"] in ("fear", "pride")
        day2_prompts = [p for p in prompts[day2_start:] if "EMOTION-WEIGHTED MEMORIES" in p[2]]
        assert {p[0] for p in day2_prompts} == {"B", "TIPPY", "MENTOR", "M"}
        assert all("terrified" in p[2] and "Never quote a painful one" in p[2] for p in day2_prompts)
        assert all("Agent M" not in p[2] for p in day2_prompts if p[0] != "M"), "B, Tippy and the Mentor still never hear about M"
        assert "14. Emotion-tagged memories" in [p for p in prompts if p[0] == "M"][0][2]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
    print("all tests passed")
