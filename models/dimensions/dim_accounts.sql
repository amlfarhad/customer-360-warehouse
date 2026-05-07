create or replace table dim_accounts as
select
    account_id,
    account_name,
    industry,
    region,
    segment,
    lifecycle_stage,
    company_size,
    created_at
from stg_crm_accounts;
