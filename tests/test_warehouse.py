import duckdb

from src.build_warehouse import build_warehouse, list_tables
from src.generate_data import generate_source_data


def test_build_warehouse_creates_customer_360_marts(tmp_path):
    raw_dir = tmp_path / "raw"
    db_path = tmp_path / "warehouse" / "customer360.duckdb"
    generate_source_data(raw_dir, seed=42, accounts=300)

    result = build_warehouse(raw_dir=raw_dir, db_path=db_path)

    expected = {
        "dim_customers",
        "dim_accounts",
        "dim_date",
        "dim_plans",
        "fct_product_usage_daily",
        "fct_subscription_revenue",
        "fct_support_tickets",
        "fct_pipeline_opportunities",
        "mart_customer_health",
        "mart_churn_risk",
        "mart_revenue_retention",
        "mart_product_adoption",
        "mart_account_summary",
    }

    assert expected.issubset(set(result.tables_built))
    assert expected.issubset(set(list_tables(db_path)))

    with duckdb.connect(str(db_path), read_only=True) as con:
        health_rows = con.execute("select count(*) from mart_customer_health").fetchone()[0]
        churn_rows = con.execute("select count(*) from mart_churn_risk").fetchone()[0]
        retention_rows = con.execute("select count(*) from mart_revenue_retention").fetchone()[0]

    assert health_rows >= 250
    assert churn_rows >= 250
    assert retention_rows > 0
