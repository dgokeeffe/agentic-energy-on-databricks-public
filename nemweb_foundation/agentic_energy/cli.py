"""Primary command line entry point for the governed NEMWEB workflow."""

from __future__ import annotations

import argparse
import importlib
from collections.abc import Callable, Sequence

_COMMAND_MODULES = {
    "land": "agentic_energy.nemweb.lander",
    "snapshot": "agentic_energy.nemweb.snapshot",
    "evidence": "agentic_energy.nemweb.evidence",
}


def _command(module_name: str) -> Callable[[Sequence[str] | None], int]:
    """Load a NEMWEB command lazily so bundle-foundation imports stay safe.

    Implementations are added by their dependency-ordered slices. Until then,
    invoking a command fails explicitly; it never falls back to the legacy
    JSONL workflow and never manufactures a dataset.
    """

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            raise RuntimeError(
                f"NEMWEB_COMMAND_NOT_IMPLEMENTED:{module_name.rsplit('.', 1)[-1]}"
            ) from exc
        raise
    command = getattr(module, "main", None)
    if not callable(command):
        raise RuntimeError(
            f"NEMWEB_COMMAND_HAS_NO_MAIN:{module_name.rsplit('.', 1)[-1]}"
        )
    return command


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Land, snapshot, or capture evidence for governed NEMWEB data"
    )
    parser.add_argument("command", choices=tuple(_COMMAND_MODULES))
    args, command_args = parser.parse_known_args(argv)
    return _command(_COMMAND_MODULES[args.command])(command_args)


if __name__ == "__main__":
    raise SystemExit(main())
