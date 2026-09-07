"""Pure idempotent reducer for Lakebase CDF current-state products."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Iterable, Mapping

from .events import event_order, validate_event


def reduce_current_state(
    events: Iterable[Mapping[str, Any]], *, key: str = "investigation_id"
) -> list[dict[str, Any]]:
    """Reduce insert/postimage/delete events while leaving audit history unchanged."""

    history = [deepcopy(dict(event)) for event in events]
    for event in history:
        validate_event(event, key=key)
    unique = {
        json.dumps(event, sort_keys=True, separators=(",", ":"), default=str): event
        for event in history
    }
    state: dict[str, dict[str, Any]] = {}
    for event in sorted(unique.values(), key=event_order):
        identifier = str(event[key])
        change = event["_pg_change_type"]
        if change == "update_preimage":
            continue
        if change == "delete":
            state.pop(identifier, None)
        else:
            state[identifier] = deepcopy(event)
    return [state[identifier] for identifier in sorted(state)]
