create or replace table stg_crm_accounts as
select
    cast(account_id as integer) as account_id,
    account_name,
    industry,
    region,
    segment,
    lifecycle_stage,
    cast(company_size as integer) as company_size,
    cast(created_at as date) as created_at
from crm_accounts
qualify row_number() over (partition by account_id order by created_at desc) = 1;
