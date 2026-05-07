create or replace table stg_crm_opportunities as
select
    cast(opportunity_id as integer) as opportunity_id,
    cast(account_id as integer) as account_id,
    stage,
    cast(amount as double) as amount,
    cast(created_at as date) as created_at,
    cast(closed_at as date) as closed_at
from crm_opportunities;
