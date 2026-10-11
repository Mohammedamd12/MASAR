select
    city_code,
    weather_date,
    temperature_2m_max,
    temperature_2m_min,
    temperature_2m_mean,
    precipitation_sum,
    wind_speed_10m_max,
    wind_gusts_10m_max,
    weather_missing
from {{ source('masar_raw', 'weather_daily') }}