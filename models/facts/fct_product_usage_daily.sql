create or replace table fct_product_usage_daily as
select
    account_id,
    cast(event_at as date) as usage_date,
    count(*) as events,
    count(distinct event_name) as distinct_features_used,
    count(*) filter (where event_name = 'integration_sync') as integration_syncs,
    count(*) filter (where event_name = 'export_report') as report_exports,
    count(*) filter (where event_name is null) as null_event_names
from stg_product_events
group by 1, 2;
