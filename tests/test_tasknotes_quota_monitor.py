"""Tests for tasknotes_quota_monitor.py — 覆盖配额解析、番茄钟统计、任务匹配三个核心函数"""

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tasknotes_quota_monitor import count_pomodoros, parse_quotas, task_done_count

PASS = FAIL = 0


def check(desc, got, expected):
    global PASS, FAIL
    if got == expected:
        print(f"  PASS  {desc}")
        PASS += 1
    else:
        print(f"  FAIL  {desc}")
        print(f"        got:      {repr(got)}")
        print(f"        expected: {repr(expected)}")
        FAIL += 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TODAY = date(2026, 3, 19)
TODAY_STR = "2026-03-19"


def make_daily_note(tmp: Path, content: str) -> dict:
    note_dir = tmp / "daily"
    note_dir.mkdir()
    (note_dir / f"{TODAY_STR}.md").write_text(content, encoding="utf-8")
    return {"daily_notes_path": str(note_dir)}


def make_data_json(tmp: Path, history: list) -> dict:
    p = tmp / "data.json"
    p.write_text(json.dumps({"pomodoroHistory": history}), encoding="utf-8")
    return {"data_json_path": str(p)}


def pomo(task_path: str, start_date: str = TODAY_STR, completed: bool = True, type_: str = "work") -> dict:
    return {"type": type_, "completed": completed, "startTime": f"{start_date}T10:00:00.000+08:00", "taskPath": task_path}


# ---------------------------------------------------------------------------
print("=== parse_quotas ===")
# ---------------------------------------------------------------------------

with tempfile.TemporaryDirectory() as _tmp:
    tmp = Path(_tmp)

    cfg = make_daily_note(
        tmp,
        "# 日记\n\n# TODOs\n\n- [[Task A]] : 5\n- [[Task B]] : 3\n",
    )
    check("basic quota parsing", parse_quotas(cfg, TODAY), {"Task A": 5, "Task B": 3})

with tempfile.TemporaryDirectory() as _tmp:
    cfg = make_daily_note(
        Path(_tmp),
        "- [[Task A]] : 5\n* [[Task B]] : 3\n",  # both - and * bullets
    )
    check("asterisk bullet", parse_quotas(cfg, TODAY), {"Task A": 5, "Task B": 3})

with tempfile.TemporaryDirectory() as _tmp:
    cfg = make_daily_note(Path(_tmp), "no todos here\n")
    check("no todos", parse_quotas(cfg, TODAY), {})

with tempfile.TemporaryDirectory() as _tmp:
    cfg = {"daily_notes_path": str(Path(_tmp) / "nonexistent")}
    check("missing file returns empty", parse_quotas(cfg, TODAY), {})

with tempfile.TemporaryDirectory() as _tmp:
    cfg = make_daily_note(
        Path(_tmp),
        "- [[Task with spaces - and dashes]] : 10\n",
    )
    check("task name with spaces and dashes", parse_quotas(cfg, TODAY), {"Task with spaces - and dashes": 10})

# ---------------------------------------------------------------------------
print("\n=== count_pomodoros ===")
# ---------------------------------------------------------------------------

with tempfile.TemporaryDirectory() as _tmp:
    tmp = Path(_tmp)
    cfg = make_data_json(
        tmp,
        [
            pomo("TaskNotes/Tasks/Task A.md"),
            pomo("TaskNotes/Tasks/Task A.md"),
            pomo("TaskNotes/Tasks/Task B.md"),
        ],
    )
    result = count_pomodoros(cfg, TODAY)
    check("counts per task path", result, {"TaskNotes/Tasks/Task A.md": 2, "TaskNotes/Tasks/Task B.md": 1})

with tempfile.TemporaryDirectory() as _tmp:
    cfg = make_data_json(
        Path(_tmp),
        [
            pomo("TaskNotes/Tasks/Task A.md", completed=False),  # incomplete
            pomo("TaskNotes/Tasks/Task A.md", type_="short-break"),  # break
            pomo("TaskNotes/Tasks/Task A.md", start_date="2026-03-18"),  # yesterday
        ],
    )
    check("excludes incomplete/break/yesterday", count_pomodoros(cfg, TODAY), {})

with tempfile.TemporaryDirectory() as _tmp:
    cfg = {"data_json_path": str(Path(_tmp) / "nonexistent.json")}
    check("missing data.json returns empty", count_pomodoros(cfg, TODAY), {})

# ---------------------------------------------------------------------------
print("\n=== task_done_count ===")
# ---------------------------------------------------------------------------

counts = {
    "TaskNotes/Tasks/Task A.md": 3,
    "TaskNotes/Tasks/Task B.md": 1,
    "TaskNotes/Archive/Old Task.md": 2,
}

check("exact suffix match", task_done_count("Task A", counts), 3)
check("match in archive folder", task_done_count("Old Task", counts), 2)
check("no match returns 0", task_done_count("Task C", counts), 0)
check("case insensitive match", task_done_count("task a", counts), 3)
check("partial name does not match", task_done_count("Task", counts), 0)

# ---------------------------------------------------------------------------
print(f"\n{'='*40}")
print(f"  {PASS} passed, {FAIL} failed")
