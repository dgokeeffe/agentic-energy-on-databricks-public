"""Root-test shim for the independently packaged ``nemweb_ml/src`` tree."""

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parent / "src" / "nemweb_ml")]
