from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, Optional

CREDENTIAL_KEYS = ["OPENAI_API_KEY", "IDA_LLM_API_KEY", "IDA_LLM_BASE_URL", "HF_TOKEN"]


def _parse_env_file(path: Path) -> Dict[str, str]:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def load_credentials(paths: Optional[Iterable[str | Path]] = None, override: bool = False) -> Dict[str, bool]:
    """Load credentials.env or .env automatically."""
    if paths is None:
        cwd = Path.cwd()
        paths = [cwd / "credentials.env", cwd / ".env", cwd.parent / "credentials.env", Path.home() / "credentials.env"]
    loaded = {}
    for path in paths:
        path = Path(path).expanduser()
        values = _parse_env_file(path)
        if not values:
            continue
        for k, v in values.items():
            if override or not os.environ.get(k):
                os.environ[k] = v
                loaded[k] = True
    return credential_status()


def credential_status() -> Dict[str, bool]:
    return {k: bool(os.environ.get(k)) for k in CREDENTIAL_KEYS}
