FROM python:3.9-slim

# تثبيت أدوات النظام الضرورية للتشفير + PostgreSQL
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# نسخ الملفات مع الحفاظ على الهيكل
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# التأكد من وجود ملفات تعريف لكل المجلدات
RUN touch crypto_engine/__init__.py idx_manager/__init__.py ingestion_api/__init__.py

# التشغيل الصحيح
CMD ["python3", "-m", "ingestion_api.server"]
