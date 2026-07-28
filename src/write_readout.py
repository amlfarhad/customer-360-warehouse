"""Write Customer 360 business reports and dashboard artifacts."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot

from src.run_quality_checks import QualityAudit


def write_quality_report(audit: QualityAudit, output_path: str | Path) -> Path:
    """Write the data quality audit as Markdown."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Data Quality Audit",
        "",
        f"Overall status: **{audit.summary.status.upper()}**",
        "",
        "| Check | Status | Severity | Observed | Threshold | Detail |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for check in audit.checks:
        lines.append(f"| {check.name} | {check.status.upper()} | {check.severity} | {check.observed} | {check.threshold} | {check.detail} |")
    path.write_text("\n".join(lines) + "\n")
    return path


def write_readout(db_path: str | Path, audit: QualityAudit, output_path: str | Path) -> Path:
    """Write executive Customer 360 readout."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path), read_only=True) as con:
        kpis = con.execute(
            """
            select
                count(*) as accounts,
                avg(h.health_score) as avg_health,
                avg(c.churn_risk_score) as avg_churn_risk,
                sum(h.recognized_revenue) as recognized_revenue,
                sum(case when churn_risk_band = 'high' then 1 else 0 end) as high_risk_accounts
            from mart_customer_health h
            join mart_churn_risk c using (account_id)
            """
        ).fetchone()
        top_risk = con.execute(
            """
            select
                h.account_name,
                h.segment,
                c.churn_risk_score,
                h.health_score,
                h.support_tickets,
                h.failed_invoice_amount
            from mart_customer_health h
            join mart_churn_risk c using (account_id)
            order by c.churn_risk_score desc, h.recognized_revenue desc
            limit 8
            """
        ).fetchdf()
        retention = con.execute("select * from mart_revenue_retention order by recognized_revenue desc").fetchdf()

    lines = [
        "# Customer 360 Executive Readout",
        "",
        "## Executive Summary",
        "",
        f"- Accounts modeled: {int(kpis[0]):,}",
        f"- Average health score: {float(kpis[1]):.1f}",
        f"- Average churn risk score: {float(kpis[2]):.1f}",
        f"- Recognized revenue in modeled invoices: ${float(kpis[3]):,.0f}",
        f"- High-risk accounts: {int(kpis[4]):,}",
        f"- Data quality status: {audit.summary.status.upper()} ({audit.summary.failed} failed, {audit.summary.warnings} warnings)",
        "",
        "## Recommendations",
        "",
        "1. Prioritize save motions for high-revenue accounts with high support load and failed invoices.",
        "2. Use product adoption gaps to focus customer success outreach before renewal windows.",
        "3. Treat missing firmographic fields and billing anomalies as blockers for automated churn scoring.",
        "",
        "## Highest-Risk Accounts",
        "",
        "| Account | Segment | Churn Risk | Health | Tickets | Failed Invoice Amount |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in top_risk.iterrows():
        lines.append(
            f"| {row['account_name']} | {row['segment']} | {row['churn_risk_score']:.1f} | "
            f"{row['health_score']:.1f} | {int(row['support_tickets'])} | ${row['failed_invoice_amount']:,.0f} |"
        )

    lines.extend(["", "## Revenue Retention by Segment", "", "| Segment | Plan | Accounts | Revenue | GRR |", "|---|---:|---:|---:|---:|"])
    for _, row in retention.iterrows():
        grr = row["gross_revenue_retention"]
        grr_text = "n/a" if pd.isna(grr) else f"{grr:.1%}"
        plan = "none" if pd.isna(row["plan"]) else row["plan"]
        lines.append(f"| {row['segment']} | {plan} | {int(row['accounts'])} | ${row['recognized_revenue']:,.0f} | {grr_text} |")

    path.write_text("\n".join(lines) + "\n")
    return path


def write_dashboard_html(db_path: str | Path, output_path: str | Path) -> Path:
    """Write a static interactive Plotly dashboard."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path), read_only=True) as con:
        health = con.execute("select * from mart_customer_health").fetchdf()
        churn = con.execute("select * from mart_churn_risk").fetchdf()
        retention = con.execute("select * from mart_revenue_retention").fetchdf()
        adoption = con.execute("select * from mart_product_adoption").fetchdf()

    health_fig = go.Figure(
        data=[go.Bar(x=health.groupby("segment")["health_score"].mean().index, y=health.groupby("segment")["health_score"].mean().values)]
    )
    health_fig.update_layout(title="Average Customer Health by Segment", yaxis_range=[0, 100])

    churn_fig = go.Figure(data=[go.Histogram(x=churn["churn_risk_score"], nbinsx=20)])
    churn_fig.update_layout(title="Churn Risk Distribution")

    retention_fig = go.Figure()
    for segment in sorted(retention["segment"].dropna().unique()):
        frame = retention[retention["segment"] == segment]
        retention_fig.add_trace(go.Bar(name=segment, x=frame["plan"].fillna("none"), y=frame["gross_revenue_retention"]))
    retention_fig.update_layout(title="Gross Revenue Retention", barmode="group", yaxis_tickformat=".0%")

    adoption_top = adoption.sort_values("adoption_rate", ascending=False).head(12)
    adoption_fig = go.Figure(data=[go.Bar(x=adoption_top["event_name"], y=adoption_top["adoption_rate"])])
    adoption_fig.update_layout(title="Top Product Adoption Rates", yaxis_tickformat=".0%")

    html = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SaaS Metrics</title>
  <style>
    body {{ margin: 28px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #172033; }}
    header {{ max-width: 1100px; margin-bottom: 24px; }}
    h1 {{ font-size: 34px; margin-bottom: 8px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }}
    .panel {{ border: 1px solid #d9dee8; border-radius: 8px; padding: 14px; background: #fff; }}
  </style>
</head>
<body>
  <header>
    <h1>SaaS Metrics</h1>
    <p>Revenue, churn risk, product adoption, and customer health from modeled CRM, billing, product, support, and marketing data.</p>
  </header>
  <section class="grid">
    <div class="panel">{plot(health_fig, include_plotlyjs="cdn", output_type="div")}</div>
    <div class="panel">{plot(churn_fig, include_plotlyjs=False, output_type="div")}</div>
    <div class="panel">{plot(retention_fig, include_plotlyjs=False, output_type="div")}</div>
    <div class="panel">{plot(adoption_fig, include_plotlyjs=False, output_type="div")}</div>
  </section>
</body>
</html>
"""
    path.write_text(html)
    return path
