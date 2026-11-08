#!/usr/bin/env python3
"""Stage 0 recon probe #2 - CLI stderr via files, recursion, list parity."""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")
from htvl import compile_source
from htvl.errors import HtvlError

CASES = [
    ("UNKNOWN_TAG", "$(dvi 'x')\n"),
    ("BAD_ARG_COUNT", "$(div 'a' 'b' 'c' 'd')\n"),
    ("UNKNOWN_VAR", "$nope\n"),
    ("UNCLOSED_CALL", "$(div 'x'\n"),
    ("UNTERMINATED_STR", "$(p 'unterminated\n"),
    ("NESTED_BAD_TAG", "$(link '' '' $(dvi 'x'))\n"),
    ("EMPTY_CALL", "$()\n"),
    ("VALID", "$(h 1 '' '' 'Hi' '')\n"),
]

print("=== Q2b: exact CLI stderr via real files ===")
for name, src in CASES:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.htvl"
        p.write_text(src)
        r = subprocess.run(
            [sys.executable, "-m", "htvl", "check", str(p), "--modern"],
            capture_output=True, text=True,
        )
        print(f"{name}: rc={r.returncode}\n  stdout={r.stdout!r}\n  stderr={r.stderr!r}")

print()
print("=== recursion / INTERNAL: 5000-deep nested calls ===")
deep = "$(link " * 5000 + "x" + ")" * 5000 + "\n"
try:
    compile_source(deep, modern=True)
    print("5000-deep: compiled OK (no RecursionError)")
except HtvlError as e:
    print(f"5000-deep: HtvlError {type(e).__name__}: {e}")
except RecursionError as e:
    print(f"5000-deep: RecursionError (-> INTERNAL code): {e}")
except Exception as e:
    print(f"5000-deep: {type(e).__name__}: {e}")

print()
print("=== legacy project balance audit ===")
legacy = Path("legacy/index.htvl").read_text()
opens, closes = {}, {}
for i, line in enumerate(legacy.splitlines(), 1):
    import re
    for m in re.finditer(r"\$\(\s*([A-Za-z_][\w-]*)", line):
        opens.setdefault(m.group(1), []).append(i)
    for m in re.finditer(r"\$_(\w+)", line):
        closes.setdefault(m.group(1), []).append(i)
print("opens:", {k: len(v) for k, v in opens.items()})
print("closes:", {k: len(v) for k, v in closes.items()})
unclosed = {t: v for t, v in opens.items() if len(v) > len(closes.get("_" + t, []))}
print("unclosed (open>close):", {t: v for t, v in unclosed.items()})

print()
print("=== htvl list output vs ELEMENTS table ===")
r = subprocess.run([sys.executable, "-m", "htvl", "list"], capture_output=True, text=True)
print("CLI rc:", r.returncode, "| first lines:")
print("\n".join(r.stdout.splitlines()[:5]))
print("...last lines:")
print("\n".join(r.stdout.splitlines()[-3:]))
