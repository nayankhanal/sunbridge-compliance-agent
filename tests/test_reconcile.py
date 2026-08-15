"""Reconciliation is pure logic, so it's the part worth unit-testing.

Runs with no API key or network -- uses the fixtures.
"""
from src.fixtures import mock_extractions
from src.reconcile import reconcile
from src.schema import ReconStatus


def _status(result, key):
    return next(f.status for f in result.fields if f.key == key)


def test_reconcile_statuses():
    result = reconcile(mock_extractions())

    # both sheets, identical -> agree
    assert _status(result, "rated_output_power") == ReconStatus.agree
    assert _status(result, "ip_rating") == ReconStatus.agree

    # same meaning, different wording -> agree_reworded
    assert _status(result, "topology") == ReconStatus.agree_reworded
    assert _status(result, "cooling") == ReconStatus.agree_reworded

    # 5.5 kW vs 5.5 kVA -> conflict
    assert _status(result, "max_power") == ReconStatus.conflict

    # weight printed twice on one sheet -> inconsistent
    assert _status(result, "weight") == ReconStatus.inconsistent

    # only present on the AM2 sheet
    assert _status(result, "overvoltage_category") == ReconStatus.only_one

    # differing standards lists -> conflict
    assert _status(result, "grid_connection_standards") == ReconStatus.conflict


def test_max_power_note_mentions_unit():
    result = reconcile(mock_extractions())
    field = next(f for f in result.fields if f.key == "max_power")
    assert "kva" in (field.note or "").lower() or "unit" in (field.note or "").lower()
    # both raw values are preserved
    assert field.values["AM2-P1"] == "5.5 kW"
    assert field.values["AM2"] == "5.5 kVA"
