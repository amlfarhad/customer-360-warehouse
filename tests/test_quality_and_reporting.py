import json

from src.build_warehouse import build_warehouse
from src.generate_data import generate_source_data
from src.run_quality_checks import run_quality_audit
from src.write_readout import write_dashboard_html, write_quality_report, write_readout


def test_quality_audit_detects_source_and_mart_issues(tmp_path):
    raw_dir = tmp_path / "raw"
    db_path = tmp_path / "customer360.duckdb"
    generate_source_data(raw_dir, seed=42, accounts=250)
    build_warehouse(raw_dir, db_path)

    audit = run_quality_audit(raw_dir=raw_dir, db_path=db_path)
    names = {check.name for check in audit.checks}

    assert "duplicate_crm_accounts" in names
    assert "missing_company_size" in names
    assert "negative_invoice_amount" in names
    assert "subscription_end_before_start" in names
    assert "churn_score_bounds" in names
    assert audit.summary.total_checks == len(audit.checks)


def test_reports_write_business_outputs(tmp_path):
    raw_dir = tmp_path / "raw"
    db_path = tmp_path / "customer360.duckdb"
    report_dir = tmp_path / "reports"
    generate_source_data(raw_dir, seed=42, accounts=250)
    build_warehouse(raw_dir, db_path)
    audit = run_quality_audit(raw_dir=raw_dir, db_path=db_path)

    quality_path = write_quality_report(audit, report_dir / "data_quality_audit.md")
    readout_path = write_readout(db_path, audit, report_dir / "customer_health_readout.md")
    dashboard_path = write_dashboard_html(db_path, report_dir / "dashboard.html")

    assert "# Data Quality Audit" in quality_path.read_text()
    assert "# Customer 360 Executive Readout" in readout_path.read_text()
    assert "Plotly.newPlot" in dashboard_path.read_text()
    assert json.dumps(audit.to_dict())
