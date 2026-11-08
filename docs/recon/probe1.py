#!/usr/bin/env python3
"""Stage 0 recon probe - evidence for docs/recon.md. Prints raw findings."""
import subprocess
import sys
import time
import traceback

sys.path.insert(0, ".")

import htvl
from htvl import compile_source
from htvl.errors import (
    HtvlArityError,
    HtvlError,
    HtvlSyntaxError,
    HtvlUnknownTagError,
    HtvlUnknownVariableError,
)

CASES = [
    ("UNKNOWN_TAG", "$(dvi 'x')\n"),
    ("BAD_ARG_COUNT", "$(div 'a' 'b' 'c' 'd')\n"),
    ("UNKNOWN_VAR", "$nope\n"),
    ("UNCLOSED_CALL", "$(div 'x'\n"),
    ("UNTERMINATED_STR", "$(p 'unterminated\n"),
    ("NESTED_BAD_TAG", "$(link '' '' $(dvi 'x'))\n"),
    ("UNKNOWN_CLOSE", "$_video\n"),
    ("MISSING_CLOSE", "$(div 'x')\n"),
    ("EMPTY_CALL", "$()\n"),
    ("VALID", "$(h 1 '' '' 'Hi' '')\n"),
]

print("=== Q1/Q2: exception types, line/column, messages ===")
for name, src in CASES:
    try:
        html = compile_source(src, modern=True)
        print(f"{name}: OK -> {html!r}")
    except HtvlError as exc:
        attrs = {
            k: getattr(exc, k, None)
            for k in ("line", "column", "message", "name", "expected", "got")
        }
        print(f"{name}: {type(exc).__name__} {attrs} | str={str(exc)!r}")
    except Exception as exc:
        print(f"{name}: UNEXPECTED {type(exc).__name__}: {exc}")

print()
print("=== Q2b: CLI stderr text (htvl check) ===")
for name, src in CASES:
    p = subprocess.run(
        [sys.executable, "-m", "htvl", "check", "-", "--modern"],
        input=src, capture_output=True, text=True,
    )
    print(f"{name}: rc={p.returncode} stdout={p.stdout!r} stderr={p.stderr!r}")

print()
print("=== Q3: tag table reachability ===")
from htvl.elements import ELEMENTS
print("ELEMENTS count:", len(ELEMENTS))
print("params attr:", {n: ELEMENTS[n].params for n in list(ELEMENTS)[:4]})
print("signature sample:", ELEMENTS["a"].signature)

print()
print("=== Q4: --modern escaping / empty attrs on adversarial input ===")
adv = {
    "amp": "$(p '' '' 'A & B' '')\n",
    "lt": "$(p '' '' '<script>alert(1)</script>' '')\n",
    "quotes": "$(p '' '' 'He said \"hi\"' '')\n",
    "attr_escape": "$(a 'x' 'https://q/?a=1&b=2' 'link' '' '' '' '')\n",
    "nested": "$(link stylesheet 'text/css' $(bsCdn '4.3.1'))\n",
}
for name, src in adv.items():
    legacy = compile_source(src, modern=False)
    modern = compile_source(src, modern=True)
    print(f"{name}:\n  legacy={legacy!r}\n  modern={modern!r}")

deep = "$(link " * 200 + "x" + ")" * 200 + "\n"
try:
    compile_source(deep, modern=True)
    print("deep nesting (200): OK")
except Exception as exc:
    print(f"deep nesting (200): {type(exc).__name__}: {exc}")

print()
print("=== Q5: nested call error line ===")
src = "$DOCTYPE_htvl\n$htvl\n\n\n$(link stylesheet 'text/css' $(dvi 'x'))\n"
try:
    compile_source(src, modern=True)
    print("no error?!")
except HtvlError as exc:
    print(f"nested error on line 5 of 6: type={type(exc).__name__} line={getattr(exc, 'line', None)} str={str(exc)!r}")

print()
print("=== Q6: size and speed ===")
for n in (1000, 10000, 50000):
    doc = "$(p '' '' 'line content here' '')\n" * n
    t0 = time.perf_counter()
    html = compile_source(doc, modern=True)
    ms = (time.perf_counter() - t0) * 1000
    print(f"{n} lines: {len(doc)} bytes -> {len(html)} bytes out in {ms:.1f} ms")
