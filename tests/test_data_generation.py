from pathlib import Path

import pandas as pd

from src.generate_data import generate_source_data


def test_generate_source_data_creates_expected_sources(tmp_path):
    manifest = generate_source_data(tmp_path, seed=42, accounts=300)

    expected = {
        "crm_accounts.csv",
        "crm_contacts.csv",
        "crm_opportunities.csv",
        "billing_subscriptions.csv",
        "billing_invoices.csv",
        "product_events.csv",
        "support_tickets.csv",
        "marketing_leads.csv",
    }

    assert {Path(path).name for path in manifest.files} == expected
    assert manifest.accounts == 300


def test_generated_sources_include_messy_operational_data(tmp_path):
    generate_source_data(tmp_path, seed=42, accounts=300)

    accounts = pd.read_csv(tmp_path / "crm_accounts.csv")
    invoices = pd.read_csv(tmp_path / "billing_invoices.csv")
    events = pd.read_csv(tmp_path / "product_events.csv")
    subscriptions = pd.read_csv(tmp_path / "billing_subscriptions.csv")

    assert accounts["account_id"].duplicated().any()
    assert accounts["company_size"].isna().any()
    assert (invoices["amount"] < 0).any()
    assert events["event_name"].isna().any()
    assert (pd.to_datetime(subscriptions["ended_at"], errors="coerce") < pd.to_datetime(subscriptions["started_at"])).any()


def test_generation_is_reproducible(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"

    generate_source_data(first, seed=7, accounts=150)
    generate_source_data(second, seed=7, accounts=150)

    pd.testing.assert_frame_equal(
        pd.read_csv(first / "product_events.csv"),
        pd.read_csv(second / "product_events.csv"),
    )
