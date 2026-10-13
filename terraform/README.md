# Terraform

يدير هذا الـRoot Module موارد Masar داخل مشروع Google Cloud
`saudi-industrial-mobility` وفي منطقة الدوحة `me-central1`:

- Cloud Storage bucket للملفات الخام.
- BigQuery datasets: `masar_raw` و`masar_staging` و`masar_marts`.
- Service Account للـpipeline بصلاحيات BigQuery وCloud Storage المحددة.

استخدم Application Default Credentials محليًا ولا تنشئ أو ترفع Service Account key إلى GitHub.

```powershell
gcloud config set project saudi-industrial-mobility
gcloud auth application-default login
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt
terraform validate
terraform plan
```

راجع خطة Terraform قبل تشغيل `terraform apply`. إعدادات الحذف الآمن تمنع حذف Bucket يحتوي ملفات أو BigQuery datasets تحتوي جداول بالخطأ.

