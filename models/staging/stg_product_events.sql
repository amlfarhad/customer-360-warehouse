create or replace table stg_product_events as
select
    cast(event_id as integer) as event_id,
    cast(account_id as integer) as account_id,
    event_name,
    cast(event_at as timestamp) as event_at,
    user_role
from product_events;
