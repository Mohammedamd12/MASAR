select
    trim(city_name) as city_name,
    cast(month_start as date) as movement_date,
    cast(entries as int) as vehicle_entries,
    cast(exits as int) as vehicle_exits
from {{ source('masar_raw', 'traffic_monthly') }}
where city_name is not null