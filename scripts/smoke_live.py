"""Live smoke test: read real images through the real Anthropic API and print what comes back.

Needs ANTHROPIC_API_KEY (in the environment or in a .env file). It costs a small amount per image.
The extracted text is printed to YOUR terminal, so use sample documents, not real people's data, for first runs.

    python scripts/smoke_live.py photo.jpg [more.png ...] [--layout auto|table|form|list]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_settings  # noqa: E402
from app.extraction import AnthropicExtractor, ExtractionError, sniff_media_type  # noqa: E402


def load_dotenv(path: Path = Path(".env")) -> None:
    """Minimal .env reader: KEY=VALUE lines. Existing environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def show(result, seconds: float, limit: int = 6) -> None:
    flagged = sum(c.low for row in result.rows for c in row)
    print(f"  layout={result.layout}  columns={len(result.columns)}  rows={len(result.rows)}  "
          f"flagged={flagged}  time={seconds:.1f}s")
    print("  columns:", " | ".join(result.columns))
    for row in result.rows[:limit]:
        print("   ", " | ".join((c.v[:24] + ("?" if c.low else "")) for c in row))
    if len(result.rows) > limit:
        print(f"    ... {len(result.rows) - limit} more rows")


def main(argv=None, extractor=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("images", nargs="+", help="image files (JPG, PNG, WebP, GIF, up to 5 MB)")
    p.add_argument("--layout", default="auto", choices=["auto", "table", "form", "list"])
    args = p.parse_args(argv)

    if extractor is None:
        load_dotenv()
        settings = load_settings()
        if not settings.api_key:
            print("No ANTHROPIC_API_KEY found. Set it in the environment or in a .env file.", file=sys.stderr)
            return 2
        extractor = AnthropicExtractor(settings.api_key, settings.model)
        print(f"model: {settings.model}")

    failures = 0
    for name in args.images:
        print(f"\n{name}")
        try:
            data = Path(name).read_bytes()
        except OSError as e:
            print(f"  cannot read file: {e.strerror}")
            failures += 1
            continue
        media_type = sniff_media_type(data)
        if media_type is None:
            print("  not a JPG, PNG, WebP, or GIF image")
            failures += 1
            continue
        start = time.perf_counter()
        try:
            result = extractor.extract(data, media_type, args.layout)
        except ExtractionError as e:
            print(f"  FAILED: {e}")
            failures += 1
            continue
        show(result, time.perf_counter() - start)
    print(f"\n{len(args.images) - failures} of {len(args.images)} images read.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
