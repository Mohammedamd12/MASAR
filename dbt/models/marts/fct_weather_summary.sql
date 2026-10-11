{{ config(materialized='table') }}

with weather_data as (
    select * from {{ ref('stg_weather') }}
)

select
    city_code,
    weather_date,
    temperature_2m_max,
    temperature_2m_min,
    temperature_2m_mean,
    precipitation_sum,
    wind_speed_10m_max
from weather_data
