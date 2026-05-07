create or replace table mart_product_adoption as
select
    a.segment,
    e.event_name,
    count(*) as events,
    count(distinct e.account_id) as adopting_accounts,
    count(distinct e.account_id)::double / nullif(count(distinct a.account_id), 0) as adoption_rate
from stg_product_events e
join dim_accounts a on e.account_id = a.account_id
where e.event_name is not null
group by 1, 2;
