"""Guard against a Windows-only bug class: reading text files with the OS default encoding.

On Linux and macOS the default is UTF-8; on Windows it is often cp1252, which cannot read characters
such as the multiplication sign or curly quotes that our web files contain.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CALLS = re.compile(r"\.(read_text|write_text)\(([^)]*)\)")


def test_text_files_are_always_read_and_written_with_an_explicit_encoding():
    offenders = []
    for folder in ("app", "tests"):
        for path in (ROOT / folder).rglob("*.py"):
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for m in CALLS.finditer(line):
                    if "encoding=" not in m.group(2):
                        offenders.append(f"{path.relative_to(ROOT)}:{n}")
    assert not offenders, "add encoding=\"utf-8\" to: " + ", ".join(offenders)
