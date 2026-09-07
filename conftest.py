"""Repository-wide import paths for the independently packaged starters."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for source in (ROOT / "nemweb_ml" / "src", ROOT / "nemweb_foundation"):
    value = str(source)
    if value not in sys.path:
        sys.path.insert(0, value)
