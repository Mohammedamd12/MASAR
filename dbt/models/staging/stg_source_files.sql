select
    trim(file_name) as file_name,
    lower(trim(dataset_type)) as dataset_type,
    nullif(trim(quarter), 'unknown') as quarter
from {{ ref('source_files') }}

