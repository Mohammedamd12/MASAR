{{ config(materialized='table') }}

with traffic_data as (
    select * from {{ ref('stg_traffic') }}
)

select
    city_name,
    date_trunc(movement_date, MONTH) as movement_month,
    sum(vehicle_entries) as total_entries,
    sum(vehicle_exits) as total_exits,
    sum(vehicle_entries + vehicle_exits) as total_movement
from traffic_data
group by 1, 2