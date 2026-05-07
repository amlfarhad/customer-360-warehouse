create or replace table stg_crm_contacts as
select
    cast(contact_id as integer) as contact_id,
    cast(account_id as integer) as account_id,
    role,
    cast(is_primary as boolean) as is_primary,
    cast(created_at as date) as created_at
from crm_contacts;
