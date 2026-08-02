import json

from src.build_warehouse import build_warehouse
from src.generate_data import generate_source_data
from src.run_quality_checks import run_quality_audit
from src.write_workspace import write_decision_workspace


def test_workspace_export_is_reproducible_and_source_backed(tmp_path):
    raw_dir = tmp_path / "raw"
    db_path = tmp_path / "warehouse" / "customer360.duckdb"
    first_path = tmp_path / "app" / "data" / "first.json"
    second_path = tmp_path / "app" / "data" / "second.json"

    generate_source_data(raw_dir, seed=42, accounts=60)
    build_warehouse(raw_dir, db_path)
    audit = run_quality_audit(raw_dir=raw_dir, db_path=db_path)

    write_decision_workspace(db_path, audit, first_path, seed=42)
    write_decision_workspace(db_path, audit, second_path, seed=42)
    first = json.loads(first_path.read_text())
    second = json.loads(second_path.read_text())

    assert first == second
    assert first["meta"]["synthetic"] is True
    assert first["meta"]["seed"] == 42
    assert len(first["queue"]) == 60
    assert set(first["accounts"]) == {str(row["account_id"]) for row in first["queue"]}
    assert first["quality"]["summary"]["total_checks"] == 10
    assert first["metric_dictionary"]
    assert first["lineage"]

    account_id = str(first["queue"][0]["account_id"])
    detail = first["accounts"][account_id]
    assert detail["records"]["crm"]
    assert "invoices" in detail["records"]
    assert "usage" in detail["trends"]
    assert "No ML model is present" in first["meta"]["model_note"]
