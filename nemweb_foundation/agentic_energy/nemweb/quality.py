"""Pure fail-closed quality contracts for NEMWEB enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Any


@dataclass(frozen=True)
class RegistrationEnrichmentQuality:
    """Aggregate quality for rows expected to use registration context."""

    total_rows: int
    known_region_rows: int
    known_fuel_rows: int

    @property
    def known_region_ratio(self) -> float:
        return self.known_region_rows / self.total_rows if self.total_rows else 0.0

    @property
    def known_fuel_ratio(self) -> float:
        return self.known_fuel_rows / self.total_rows if self.total_rows else 0.0

    def validate(self, *, registration_context_expected: bool) -> None:
        if not registration_context_expected:
            return
        if self.total_rows < 1:
            raise ValueError("registration context was expected but no enriched rows were present")
        if self.known_region_rows < 1:
            raise ValueError("registration enrichment is unhealthy: all regions are UNKNOWN")
        if self.known_fuel_rows < 1:
            raise ValueError("registration enrichment is unhealthy: all fuels are UNKNOWN")


def registration_enrichment_quality(
    rows: Iterable[Mapping[str, Any]],
) -> RegistrationEnrichmentQuality:
    """Summarise enrichment without rejecting valid individual pseudo units."""

    materialised = list(rows)
    return RegistrationEnrichmentQuality(
        total_rows=len(materialised),
        known_region_rows=sum(str(row.get("region_id", "UNKNOWN")).upper() != "UNKNOWN" for row in materialised),
        known_fuel_rows=sum(str(row.get("fuel_type", "UNKNOWN")).upper() != "UNKNOWN" for row in materialised),
    )


def validate_registration_enrichment_counts(
    *,
    total_rows: int,
    known_region_rows: int,
    known_fuel_rows: int,
    registration_context_expected: bool,
) -> RegistrationEnrichmentQuality:
    quality = RegistrationEnrichmentQuality(total_rows, known_region_rows, known_fuel_rows)
    quality.validate(registration_context_expected=registration_context_expected)
    return quality
