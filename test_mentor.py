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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
    print("all tests passed")
