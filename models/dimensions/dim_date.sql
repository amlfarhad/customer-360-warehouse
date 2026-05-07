create or replace table dim_date as
select
    date_day,
    extract(year from date_day) as year,
    extract(month from date_day) as month,
    date_trunc('quarter', date_day) as quarter_start
from generate_series(date '2025-01-01', date '2026-12-31', interval 1 day) as t(date_day);
