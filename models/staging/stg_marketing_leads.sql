create or replace table stg_marketing_leads as
select
    cast(lead_id as integer) as lead_id,
    cast(account_id as integer) as account_id,
    source,
    cast(score as integer) as score,
    cast(created_at as date) as created_at,
    cast(converted as boolean) as converted
from marketing_leads;
