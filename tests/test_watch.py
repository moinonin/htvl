"""Watch mode and incremental build tests.

The watcher runs a polling loop, so the tests drive it from a background
thread with a stop event instead of sleeping for real seconds.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from htvl.project import ProjectBuilder
from htvl.watch import watch_project


def _make_project(tmp_path):
    (tmp_path / "index.htvl").write_text(
        "$(h 1 '' '' 'First' '')\n", encoding="utf-8"
    )
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "part.htvl").write_text(
        "$br\n", encoding="utf-8"
    )
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "a.txt").write_text("asset\n", encoding="utf-8")
    return tmp_path


def _start_watcher(root, modern=False):
    stop = threading.Event()
    thread = threading.Thread(
        target=watch_project,
        kwargs=dict(
            root=root,
            modern=modern,
            interval=0.05,
            stop_event=stop,
            printer=lambda _line: None,
        ),
        daemon=True,
    )
    thread.start()
    return thread, stop


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture
def project(tmp_path):
    return _make_project(tmp_path)


def test_once_compiles_everything(project):
    output = project / "public" / "index.html"
    watch_project(project, once=True, printer=lambda _line: None)
    assert "<h1" in _read(output)
    assert (project / "public" / "assets" / "a.txt").exists()


def test_edit_recompiles_incrementally(project):
    output = project / "public" / "index.html"
    watch_project(project, once=True, printer=lambda _line: None)
    assert "First" in _read(output)

    thread, stop = _start_watcher(project)
    try:
        # Give the loop time to take its first snapshot.
        time.sleep(0.2)
        (project / "index.htvl").write_text(
            "$(h 1 '' '' 'Second' '')\n", encoding="utf-8"
        )
        deadline = time.time() + 3
        while time.time() < deadline:
            if "Second" in _read(output):
                break
            time.sleep(0.05)
        assert "Second" in _read(output)
        assert "First" not in _read(output)
    finally:
        stop.set()
        thread.join(timeout=3)


def test_template_edit_recompiles_all(project):
    output = project / "public" / "index.html"
    watch_project(project, once=True, printer=lambda _line: None)
    assert "<br>" not in _read(output)

    thread, stop = _start_watcher(project)
    try:
        time.sleep(0.2)
        (project / "index.htvl").write_text(
            "$(h 1 '' '' 'Title' '')\n$part\n", encoding="utf-8"
        )
        time.sleep(0.4)
        # The template itself still emits <br>; now it should be included.
        (project / "templates" / "part.htvl").write_text(
            "$(h 2 '' '' 'Part' '')\n", encoding="utf-8"
        )
        deadline = time.time() + 3
        while time.time() < deadline:
            if ">Part<" in _read(output):
                break
            time.sleep(0.05)
        assert ">Part<" in _read(output)
    finally:
        stop.set()
        thread.join(timeout=3)


def test_new_file_is_compiled(project):
    watch_project(project, once=True, printer=lambda _line: None)
    second = project / "public" / "about.html"
    assert not second.exists()

    thread, stop = _start_watcher(project)
    try:
        time.sleep(0.2)
        (project / "about.htvl").write_text(
            "$(h 1 '' '' 'About' '')\n", encoding="utf-8"
        )
        deadline = time.time() + 3
        while time.time() < deadline:
            if second.exists():
                break
            time.sleep(0.05)
        assert second.exists()
        assert "About" in _read(second)
    finally:
        stop.set()
        thread.join(timeout=3)


def test_deleted_file_has_output_removed(project):
    watch_project(project, once=True, printer=lambda _line: None)
    output = project / "public" / "index.html"
    assert output.exists()

    thread, stop = _start_watcher(project)
    try:
        time.sleep(0.2)
        (project / "index.htvl").unlink()
        deadline = time.time() + 3
        while time.time() < deadline:
            if not output.exists():
                break
            time.sleep(0.05)
        assert not output.exists()
    finally:
        stop.set()
        thread.join(timeout=3)


def test_broken_edit_does_not_kill_the_watcher(project):
    output = project / "public" / "index.html"
    events = []
    watch_project(
        project, once=True, printer=events.append
    )

    thread, stop = _start_watcher(project)
    try:
        time.sleep(0.2)
        (project / "index.htvl").write_text(
            "$(nope 'x')\n", encoding="utf-8"
        )
        time.sleep(0.4)
        # The old output survives; the watcher is still alive.
        assert "First" in _read(output)
        (project / "index.htvl").write_text(
            "$(h 1 '' '' 'Recovered' '')\n", encoding="utf-8"
        )
        deadline = time.time() + 3
        while time.time() < deadline:
            if "Recovered" in _read(output):
                break
            time.sleep(0.05)
        assert "Recovered" in _read(output)
    finally:
        stop.set()
        thread.join(timeout=3)


def test_modern_mode_watch(project):
    output = project / "public" / "index.html"
    watch_project(
        project, once=True, modern=True, printer=lambda _line: None
    )
    assert '<h1>First</h1>' in _read(output)

    thread, stop = _start_watcher(project, modern=True)
    try:
        time.sleep(0.2)
        (project / "index.htvl").write_text(
            "$(h 1 '' '' 'Clean' '')\n", encoding="utf-8"
        )
        deadline = time.time() + 3
        while time.time() < deadline:
            if ">Clean<" in _read(output):
                break
            time.sleep(0.05)
        assert "<h1>Clean</h1>" in _read(output)
    finally:
        stop.set()
        thread.join(timeout=3)


def test_builder_output_paths(project):
    builder = ProjectBuilder(project)
    assert builder.output_for(project / "index.htvl") == (
        project / "public" / "index.html"
    )
    assert builder.output_for(project / "api.cal") == project / "cal" / "api"
    assert builder.invalidate_templates() is None
