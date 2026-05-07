"""Generate deterministic messy SaaS source data for Customer 360 analytics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SourceManifest:
    """Generated source data manifest."""

    files: list[Path]
    accounts: int
    seed: int


def _dates(start: str, days: np.ndarray) -> pd.Series:
    return pd.Series(pd.Timestamp(start) + pd.to_timedelta(days, unit="D"))


def generate_source_data(output_dir: str | Path, seed: int = 42, accounts: int = 500) -> SourceManifest:
    """Generate raw CRM, billing, product, support, and marketing CSVs."""

    rng = np.random.default_rng(seed)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    account_ids = np.arange(10001, 10001 + accounts)
    segments = rng.choice(["startup", "mid_market", "enterprise"], size=accounts, p=[0.42, 0.38, 0.20])
    industries = rng.choice(["SaaS", "Fintech", "Healthcare", "Retail", "Logistics"], size=accounts)
    regions = rng.choice(["NA", "EMEA", "APAC", "LATAM"], size=accounts, p=[0.56, 0.22, 0.16, 0.06])
    lifecycle = rng.choice(["lead", "trial", "customer", "churned"], size=accounts, p=[0.12, 0.14, 0.66, 0.08])
    company_size = rng.choice([25, 75, 150, 400, 900, 2500, None], size=accounts, p=[0.16, 0.21, 0.22, 0.18, 0.11, 0.06, 0.06])
    created_at = _dates("2024-01-01", rng.integers(0, 650, size=accounts)).dt.date.astype(str)

    crm_accounts = pd.DataFrame(
        {
            "account_id": account_ids,
            "account_name": [f"Account {i}" for i in account_ids],
            "industry": industries,
            "region": regions,
            "segment": segments,
            "lifecycle_stage": lifecycle,
            "company_size": company_size,
            "created_at": created_at,
        }
    )
    duplicates = crm_accounts.sample(max(4, accounts // 100), random_state=seed).copy()
    crm_accounts = pd.concat([crm_accounts, duplicates], ignore_index=True)

    contacts = []
    contact_id = 1
    for account_id in account_ids:
        for _ in range(int(rng.integers(1, 5))):
            contacts.append(
                {
                    "contact_id": contact_id,
                    "account_id": account_id,
                    "role": rng.choice(["admin", "buyer", "user", "executive"], p=[0.28, 0.18, 0.44, 0.10]),
                    "is_primary": contact_id % 3 == 0,
                    "created_at": _dates("2024-01-01", np.array([int(rng.integers(0, 650))])).iloc[0].date().isoformat(),
                }
            )
            contact_id += 1
    crm_contacts = pd.DataFrame(contacts)

    opportunities = []
    opp_id = 1
    for account_id, segment in zip(account_ids, segments, strict=True):
        if rng.random() < 0.72:
            amount = {"startup": 12000, "mid_market": 42000, "enterprise": 145000}[str(segment)] * rng.uniform(0.6, 1.7)
            opportunities.append(
                {
                    "opportunity_id": opp_id,
                    "account_id": account_id,
                    "stage": rng.choice(["prospecting", "qualified", "proposal", "closed_won", "closed_lost"]),
                    "amount": round(float(amount), 2),
                    "created_at": _dates("2025-01-01", np.array([int(rng.integers(0, 420))])).iloc[0].date().isoformat(),
                    "closed_at": _dates("2025-05-01", np.array([int(rng.integers(0, 300))])).iloc[0].date().isoformat(),
                }
            )
            opp_id += 1
    crm_opportunities = pd.DataFrame(opportunities)

    plan_by_segment = {"startup": "starter", "mid_market": "growth", "enterprise": "enterprise"}
    subscriptions = []
    invoices = []
    sub_id = 1
    invoice_id = 1
    for account_id, segment, stage in zip(account_ids, segments, lifecycle, strict=True):
        if stage in {"customer", "churned"}:
            plan = plan_by_segment[str(segment)]
            monthly_arr = {"starter": 900, "growth": 3500, "enterprise": 12500}[plan] * rng.uniform(0.75, 1.45)
            started_at = pd.Timestamp("2025-01-01") + pd.to_timedelta(int(rng.integers(0, 390)), unit="D")
            ended_at = pd.NaT
            if stage == "churned":
                ended_at = started_at + pd.to_timedelta(int(rng.integers(60, 360)), unit="D")
            subscriptions.append(
                {
                    "subscription_id": sub_id,
                    "account_id": account_id,
                    "plan": plan,
                    "status": "canceled" if stage == "churned" else "active",
                    "started_at": started_at.date().isoformat(),
                    "ended_at": "" if pd.isna(ended_at) else ended_at.date().isoformat(),
                    "mrr": round(float(monthly_arr), 2),
                }
            )
            for month in range(1, 13):
                invoice_date = started_at + pd.DateOffset(months=month)
                paid = rng.random() > (0.08 if stage == "churned" else 0.03)
                invoices.append(
                    {
                        "invoice_id": invoice_id,
                        "subscription_id": sub_id,
                        "account_id": account_id,
                        "invoice_date": invoice_date.date().isoformat(),
                        "amount": round(float(monthly_arr), 2),
                        "status": "paid" if paid else "failed",
                    }
                )
                invoice_id += 1
            sub_id += 1
    billing_subscriptions = pd.DataFrame(subscriptions)
    billing_invoices = pd.DataFrame(invoices)
    if len(billing_subscriptions) > 2:
        billing_subscriptions.loc[billing_subscriptions.index[0], "ended_at"] = "2024-01-01"
    if len(billing_invoices) > 5:
        billing_invoices.loc[billing_invoices.sample(max(2, len(billing_invoices) // 200), random_state=seed).index, "amount"] = -25.00

    events = []
    event_id = 1
    event_names = ["login", "create_project", "invite_user", "export_report", "integration_sync", "dashboard_view"]
    for account_id, segment, stage in zip(account_ids, segments, lifecycle, strict=True):
        base_events = {"startup": 35, "mid_market": 95, "enterprise": 210}[str(segment)]
        activity_multiplier = 0.28 if stage == "churned" else 1.0 if stage == "customer" else 0.35
        n_events = int(rng.poisson(base_events * activity_multiplier))
        for _ in range(max(2, n_events)):
            events.append(
                {
                    "event_id": event_id,
                    "account_id": account_id,
                    "event_name": rng.choice(event_names),
                    "event_at": _dates("2026-01-01", np.array([int(rng.integers(0, 120))])).iloc[0].strftime("%Y-%m-%d %H:%M:%S"),
                    "user_role": rng.choice(["admin", "member", "viewer"]),
                }
            )
            event_id += 1
    product_events = pd.DataFrame(events)
    product_events.loc[product_events.sample(max(3, len(product_events) // 500), random_state=seed).index, "event_name"] = None

    tickets = []
    ticket_id = 1
    for account_id, segment, stage in zip(account_ids, segments, lifecycle, strict=True):
        ticket_lambda = {"startup": 0.9, "mid_market": 1.8, "enterprise": 4.5}[str(segment)] * (2.2 if stage == "churned" else 1.0)
        for _ in range(int(rng.poisson(ticket_lambda))):
            tickets.append(
                {
                    "ticket_id": ticket_id,
                    "account_id": account_id,
                    "created_at": _dates("2026-01-01", np.array([int(rng.integers(0, 120))])).iloc[0].strftime("%Y-%m-%d %H:%M:%S"),
                    "category": rng.choice(["billing", "bug", "how_to", "integration"]),
                    "priority": rng.choice(["low", "medium", "high", "urgent"], p=[0.34, 0.40, 0.19, 0.07]),
                    "resolved_hours": round(float(max(1, rng.normal(28, 14))), 1),
                }
            )
            ticket_id += 1
    support_tickets = pd.DataFrame(tickets)

    leads = []
    lead_id = 1
    for account_id, stage in zip(account_ids, lifecycle, strict=True):
        if rng.random() < 0.55:
            leads.append(
                {
                    "lead_id": lead_id,
                    "account_id": account_id,
                    "source": rng.choice(["webinar", "paid_search", "organic", "event", "partner"]),
                    "score": int(rng.integers(15, 100)),
                    "created_at": _dates("2025-01-01", np.array([int(rng.integers(0, 460))])).iloc[0].date().isoformat(),
                    "converted": stage in {"customer", "churned"} and rng.random() < 0.75,
                }
            )
            lead_id += 1
    marketing_leads = pd.DataFrame(leads)

    outputs = {
        "crm_accounts.csv": crm_accounts,
        "crm_contacts.csv": crm_contacts,
        "crm_opportunities.csv": crm_opportunities,
        "billing_subscriptions.csv": billing_subscriptions,
        "billing_invoices.csv": billing_invoices,
        "product_events.csv": product_events,
        "support_tickets.csv": support_tickets,
        "marketing_leads.csv": marketing_leads,
    }
    files = []
    for filename, frame in outputs.items():
        path = output_path / filename
        frame.to_csv(path, index=False)
        files.append(path)

    return SourceManifest(files=files, accounts=accounts, seed=seed)
