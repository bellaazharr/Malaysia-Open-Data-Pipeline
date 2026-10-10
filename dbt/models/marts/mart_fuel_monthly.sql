-- Gold: monthly averages for the dashboard
select
    date_trunc('month', price_date)::date as month,
    round(avg(ron95), 2)   as avg_ron95,
    round(avg(ron97), 2)   as avg_ron97,
    round(avg(diesel), 2)  as avg_diesel,
    max(ron97) - min(ron97) as ron97_monthly_range
from {{ ref('stg_fuelprice') }}
group by 1
order by 1