create or replace table fct_pipeline_opportunities as
select
    opportunity_id,
    account_id,
    stage,
    amount,
    created_at,
    closed_at,
    case when stage = 'closed_won' then amount else 0 end as won_amount,
    case when stage = 'closed_lost' then amount else 0 end as lost_amount
from stg_crm_opportunities;
