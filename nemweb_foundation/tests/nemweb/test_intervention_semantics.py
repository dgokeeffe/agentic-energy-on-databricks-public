from agentic_energy.nemweb.corrections import mark_effective_intervention


def test_intervention_pair_is_retained_and_highest_flag_is_effective() -> None:
    rows = [
        {"interval_end": "2024-01-01T00:05:00+10:00", "region_id": "NSW1", "intervention": 0, "price": -50.0},
        {"interval_end": "2024-01-01T00:05:00+10:00", "region_id": "NSW1", "intervention": 1, "price": 250.0},
    ]
    actual = mark_effective_intervention(rows, ("interval_end", "region_id"))
    assert len(actual) == 2
    assert [row["intervention"] for row in actual if row["is_effective_run"]] == [1]
    assert rows == [
        {"interval_end": "2024-01-01T00:05:00+10:00", "region_id": "NSW1", "intervention": 0, "price": -50.0},
        {"interval_end": "2024-01-01T00:05:00+10:00", "region_id": "NSW1", "intervention": 1, "price": 250.0},
    ]


def test_non_intervention_is_effective_when_it_is_the_only_run() -> None:
    actual = mark_effective_intervention(
        [{"interval_end": "2024-01-01T00:10:00+10:00", "region_id": "VIC1", "intervention": 0}],
        ("interval_end", "region_id"),
    )
    assert actual[0]["is_effective_run"] is True
