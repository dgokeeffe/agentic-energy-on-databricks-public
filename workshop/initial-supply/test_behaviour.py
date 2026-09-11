"""Executable Given/When/Then examples using the actual authored SELECT.

SQLite verifies aggregation behavior, not Spark analysis or pipeline execution.
The input contract is the baseline Gold unit table: unique (interval_end, duid),
nonnull MW, deterministic attribution, corrections already selected by Silver.
"""
import json
from pathlib import Path
import sqlite3

import pytest

from agentic_energy.labs.initial_supply import initial_supply_sql

SCENARIOS = json.loads(Path(__file__).with_name("scenarios.json").read_text())
COLUMNS = ["interval_end", "region_id", "actual_supply_mw", "observed_unit_count",
           "partially_enriched_unit_count", "source_publication_at"]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["name"])
def test_given_unit_observations_when_supply_is_evaluated_then_contract_holds(scenario):
    with sqlite3.connect(":memory:") as connection:
        # Given corrected and enriched unit observations, including signed storage.
        connection.execute("""CREATE TABLE gold_nem_unit_dispatch_5min (
            interval_end TEXT, region_id TEXT, duid TEXT, actual_generation_mw REAL,
            dimension_match_status TEXT, source_publication_at TEXT,
            PRIMARY KEY (interval_end, duid))""")
        connection.executemany("INSERT INTO gold_nem_unit_dispatch_5min VALUES (?,?,?,?,?,?)", scenario["given"])

        def evaluate():
            # When the learner's production SELECT runs, assert its public schema too.
            cursor = connection.execute(initial_supply_sql())
            assert [item[0] for item in cursor.description] == COLUMNS
            return sorted([list(row) for row in cursor.fetchall()], key=lambda row: row[:2])

        # Then compare concrete outcomes, not source-code strings or an alternate implementation.
        assert evaluate() == scenario["then"]
        assert evaluate() == scenario["then"], "Repeat evaluation must be stable"
        if "correction" in scenario:
            correction = scenario["correction"]
            connection.execute("UPDATE gold_nem_unit_dispatch_5min SET actual_generation_mw=? WHERE duid=?",
                               (correction["mw"], correction["duid"]))
            assert evaluate() == scenario["then_corrected"]
