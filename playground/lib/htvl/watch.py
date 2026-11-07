"""Watch mode: recompile a project whenever its files change.

Dependency-free by design - a plain polling loop (``os.stat`` on every watched
file, ``interval`` times per second) is more than fast enough for an authoring
tool and keeps the install to the standard library.

Changes are handled incrementally:

* a ``.htvl`` / ``.cal`` file changed or appeared -> recompile just that file
* one disappeared -> delete its output
* anything under ``templates/`` changed -> full recompile
* anything under ``assets/`` changed -> re-copy ``assets/``

Editors routinely save the same logical change as several filesystem events,
so each poll round collects everything that changed and applies it once.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .project import ProjectBuilder

# (path, mtime_ns, size) is enough to notice edits, creations and deletions.
_Snapshot = Dict[Path, Tuple[int, int]]

_DEBOUNCE = 0.05


def _snapshot(builder: ProjectBuilder) -> _Snapshot:
    """Record the state of every file the project output depends on."""
    snapshot: _Snapshot = {}
    roots = [builder.root / "templates", builder.root / "assets"]
    for path in builder.sources():
        _record(snapshot, path)
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                _record(snapshot, Path(dirpath) / name)
    return snapshot


def _record(snapshot: _Snapshot, path: Path) -> None:
    try:
        stat = path.stat()
    except OSError:
        return
    snapshot[path.resolve()] = (stat.st_mtime_ns, stat.st_size)


def _diff(old: _Snapshot, new: _Snapshot) -> Tuple[List[Path], List[Path]]:
    """Return (changed_or_added, deleted)."""
    changed = [p for p, state in new.items() if old.get(p) != state]
    deleted = [p for p in old if p not in new]
    return changed, deleted


def _relative_to(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def watch_project(
    root: Path,
    out_dir: str = "public",
    modern: bool = False,
    interval: float = 0.5,
    printer: Optional[Callable[[str], None]] = None,
    stop_event: Optional[threading.Event] = None,
    once: bool = False,
) -> None:
    """Compile ``root``, then keep it compiled forever (until Ctrl-C).

    ``once`` returns immediately after the first compile - handy for tests.
    ``stop_event`` stops the loop from another thread.
    ``printer`` receives a human-readable line for every action taken.
    """
    say = printer if printer is not None else (lambda _line: None)
    builder = ProjectBuilder(root, out_dir=out_dir, modern=modern)

    result = builder.compile_all()
    for output in result.outputs:
        say(f"compiled {_relative_to(output, builder.root)}")
    if result.copied_assets:
        say(f"copied assets -> {_relative_to(result.copied_assets, builder.root)}")
    say(f"watching '{builder.root}' (Ctrl-C to stop)")

    if once:
        return

    previous = _snapshot(builder)
    while stop_event is None or not stop_event.is_set():
        if stop_event is not None:
            if stop_event.wait(interval):
                return
        else:
            time.sleep(interval)

        current = _snapshot(builder)
        changed, deleted = _diff(previous, current)
        if not changed and not deleted:
            continue

        # A single save often shows up as several events; settle briefly and
        # re-read so one edit produces one recompile.
        time.sleep(_DEBOUNCE)
        current = _snapshot(builder)
        changed, deleted = _diff(previous, current)
        previous = current

        reload_templates = any(
            _is_within(path, builder.root / "templates") for path in changed
        )
        touched = False

        for path in changed:
            if path.suffix in (".htvl", ".cal") and _is_within(path, builder.root):
                try:
                    output = builder.compile_one(path)
                except Exception as exc:  # keep watching through errors
                    say(f"error in {_relative_to(path, builder.root)}: {exc}")
                    continue
                say(f"compiled {_relative_to(output, builder.root)}")
                touched = True
            elif _is_within(path, builder.root / "assets"):
                copied = builder.sync_assets()
                if copied is not None:
                    say(
                        "copied assets -> "
                        f"{_relative_to(copied, builder.root)}"
                    )
                touched = True
            elif reload_templates:
                pass  # covered by the full rebuild below

        for path in deleted:
            if path.suffix in (".htvl", ".cal"):
                removed = builder.remove_output(path)
                if removed is not None:
                    say(f"removed {_relative_to(removed, builder.root)}")
                    touched = True

        if reload_templates or (changed and not touched):
            try:
                builder.invalidate_templates()  # pick up template changes
                result = builder.compile_all()
            except Exception as exc:  # keep watching through errors
                say(f"error: {exc}")
                continue
            for output in result.outputs:
                say(f"compiled {_relative_to(output, builder.root)}")

        if not changed and not deleted:
            say("nothing to do")


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True
