# Decision workspace

The public sample workspace lives in `app/` and is intentionally static. It reads `app/data/workspace.json`, which is generated from the same DuckDB warehouse used by the existing reports.

## Operator flow

1. Start in the portfolio queue, sorted by the existing churn-risk score and then recognized revenue.
2. Filter by risk band, segment, lifecycle stage, or account search.
3. Open an account to inspect the score drivers, monthly trends, source records, and related pipeline rows.
4. Choose and save a recommended next action. This is stored in the current browser only.
5. Export the filtered queue or the account brief for a decision-ready handoff.
6. Use Definitions & lineage to inspect metric boundaries, source coverage, and the data-quality audit.

## Evidence language

- **Observed** means a value is directly present in a source or modeled fact table: invoice status, recognized revenue, product events, support tickets, CRM lifecycle, and feature variety.
- **Heuristic** means a deterministic rule used to sort attention or calculate the existing 0–100 health/churn scores. These are not probabilities and do not prove an outcome.
- **Model-derived** is shown explicitly as empty because this repository does not contain an ML model or validated probability.

## Rebuild the payload

```bash
python3 -m src.cli demo --workspace . --accounts 500 --seed 42
```

The output is deterministic for the same seed and account count. The generated JSON contains queue rows, account-level source records, monthly trends, segment comparisons, metric definitions, lineage, source coverage, and the quality audit.

## Limitations

- The source data is synthetic and intentionally messy. Duplicate account inputs, negative invoice amounts, invalid subscription dates, missing firmographics, and null event names remain visible to the audit.
- The warehouse's health and churn calculations are existing SQL heuristics. They are not validated against customer outcomes.
- The static app has no authentication, backend, or external system writeback. Browser-local actions are convenience notes for a sample workflow.
- The app does not accept uploads. That keeps the public demo bounded to the reproducible repository pipeline.
