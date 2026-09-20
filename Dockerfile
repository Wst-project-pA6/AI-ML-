# استخدام نسخة Python الرسمية والحديثة
FROM python:3.11-slim

# تحديد مجلد العمل داخل الحاوية
WORKDIR /app

# تثبيت متطلبات النظام الأساسية
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt-get/lists/*

# نسخ ملف المتطلبات أولاً للاستفادة من Docker Cache
COPY requirements.txt .

# تثبيت المكتبات البرمجية
RUN pip install --no-cache-dir -r requirements.txt

# نسخ بقية ملفات المشروع والنماذج إلى الحاوية
COPY . .

# فتح المنفذ 8000
EXPOSE 8000

# أمر تشغيل خادم Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
