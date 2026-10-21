"""Settings read from environment variables. No files, no database."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    api_key: str | None = None
    demo_mode: bool = False
    model: str = "claude-sonnet-5-5"
    max_upload_bytes: int = 5 * 1024 * 1024  # 5 MB, the API's per-image limit


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    return Settings(
        api_key=env.get("ANTHROPIC_API_KEY") or None,
        demo_mode=env.get("DEMO_MODE", "").strip().lower() in {"1", "true", "yes"},
        model=env.get("EXTRACT_MODEL") or Settings.model,
        max_upload_bytes=int(float(env.get("MAX_UPLOAD_MB", "5")) * 1024 * 1024),
    )
