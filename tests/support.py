"""Shared test bootstrap: put src/ and the frozen legacy fixture on sys.path."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for _path in (ROOT / "src", ROOT / "tests" / "legacy"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
