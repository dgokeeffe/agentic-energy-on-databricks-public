"""Point-in-time feature helpers; no model is trained by this module."""

from __future__ import annotations

from typing import Any, Mapping

FEATURE_COLUMNS = (
    "price_aud_per_mwh",
    "demand_mw",
    "recent_price_volatility",
    "market_wide_binding_constraint_count",
    "market_wide_interconnector_source_sign_flow_mw",
)


def feature_vector(row: Mapping[str, Any]) -> list[float]:
    missing = [name for name in FEATURE_COLUMNS if row.get(name) is None]
    if missing:
        raise ValueError(f"missing model features: {missing}")
    return [float(row[name]) for name in FEATURE_COLUMNS]
