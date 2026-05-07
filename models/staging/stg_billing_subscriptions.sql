create or replace table stg_billing_subscriptions as
select
    cast(subscription_id as integer) as subscription_id,
    cast(account_id as integer) as account_id,
    plan,
    status,
    cast(started_at as date) as started_at,
    try_cast(nullif(cast(ended_at as varchar), '') as date) as ended_at,
    cast(mrr as double) as mrr
from billing_subscriptions;
