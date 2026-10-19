"""Run with:  python test_mentor.py   (no API key or email needed)"""
import datetime as dt
import json
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


def test_notebook_pruning_keeps_pinned_lines():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "n.md"
        p.write_text("# Title\n* pinned seed\n", encoding="utf-8")
        mentor.append_lines(p, [f"note {i}" for i in range(60)], "2026-10-19")
        lines = p.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "# Title" and lines[1] == "* pinned seed"
        assert len(lines) == 2 + mentor.MAX_NOTEBOOK_LINES
        assert lines[-1].endswith("note 59")


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
        assert "Day 1" in (data / "daylog.md").read_text(encoding="utf-8")
        assert "Used habit stacking" in (data / "notebook_b.md").read_text(encoding="utf-8")
        assert "APPROVE" in (data / "notebook_m.md").read_text(encoding="utf-8")
        assert json.loads((data / "state.json").read_text())["last_sent"] == "2026-10-19"
        # B and S must never be told about M
        for name in ("notebook_b.md", "notebook_s.md"):
            assert "Agent M" not in (data / name).read_text(encoding="utf-8").replace("Agent M log", "")


def test_unusable_m_verdict_never_sends_unreviewed_draft():
    original = mentor.agent_m
    mentor.agent_m = lambda *a, **k: None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            shutil.copytree("data", data)
            args = mentor.argparse.Namespace(data_dir=str(data), date="2026-10-19", force=False, mock=True, dry_run=False)
            mentor.run(args)
            assert "BLOCK" in (data / "notebook_m.md").read_text(encoding="utf-8")
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
    assert llm.provider == "groq" and llm.model == "llama-3.3-70b-versatile"
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
        out = mentor.LLM().ask("[S] sys", "hi", 100, json_mode=True)
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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
    print("all tests passed")
