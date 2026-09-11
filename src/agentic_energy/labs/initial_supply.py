"""Regional observed supply from the correction-aware, enriched unit product."""


def initial_supply_sql():
    """Keep signed MW and missing attribution at region/interval grain.

    Input has one nonnull output observation per (interval_end, duid). Upstream
    Silver owns correction selection; registration owns region/fuel attribution.
    This SELECT never adds capacity, interconnector flow or unobserved generation.
    """
    return """
        SELECT interval_end, region_id,
               SUM(actual_generation_mw) AS actual_supply_mw,
               COUNT(DISTINCT duid) AS observed_unit_count,
               SUM(CASE WHEN dimension_match_status <> 'REGION_AND_FUEL'
                        THEN 1 ELSE 0 END) AS partially_enriched_unit_count,
               MAX(source_publication_at) AS source_publication_at
        FROM gold_nem_unit_dispatch_5min
        GROUP BY interval_end, region_id
    """
