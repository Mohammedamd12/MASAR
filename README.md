# Masar | مسار

مشروع لتحليل ملفات فعاليات القطاع العام وحركة المرور باستخدام أدوات الـCore المطلوبة:

- Docker Compose لتشغيل البيئة محليًا.
- Apache Airflow لتنظيم الـpipeline.
- dbt لتنظيف وتحويل البيانات.
- Terraform لتهيئة البنية التحتية لاحقًا.
- Streamlit لعرض النتائج.



## الهيكلة

```text
MASAR/
├── airflow/          # DAGs وصورة Airflow
├── dbt/              # models, tests, seeds
├── streamlit/        # لوحة العرض
├── terraform/        # قالب البنية التحتية
├── data/processed/   # ملفات ناتجة (لا تُرفع إلى Git)
├── scripts/          # أوامر مساعدة لـ Windows
├── docker-compose.yml
└── *.xlsx            # ملفات البيانات الأصلية
```

## التشغيل لأول مرة

المتطلبات: Docker Desktop مع Docker Compose حديث، ويفضل تخصيص 4 GB ذاكرة على الأقل لـDocker.

من Terminal داخل VS Code:

```powershell
Copy-Item .env.example .env
docker compose build
docker compose up airflow-init
docker compose up -d
```

بعد التشغيل:

- Airflow: <http://localhost:8080>
- Streamlit: <http://localhost:8501>

شغّل DAG باسم `masar_core_pipeline` من Airflow. سيقوم بقراءة معلومات ملفات Excel، ثم يشغّل `dbt seed` و`dbt run` و`dbt test`.

للإيقاف:

```powershell
docker compose down
```

## أوامر مفيدة

```powershell
# فحص إعداد Docker Compose
docker compose config

# مشاهدة السجلات
docker compose logs -f airflow-scheduler

# تشغيل dbt يدويًا داخل Airflow
docker compose run --rm airflow-cli bash -lc "cd /opt/airflow/project/dbt && dbt build --profiles-dir ."

# فحص Terraform بدون إنشاء موارد
Set-Location terraform
terraform init
terraform fmt -check
terraform validate
```

> ملف `.env` محلي ولا يُرفع إلى Git. غيّر كلمة مرور PostgreSQL قبل مشاركة البيئة.

