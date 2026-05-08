FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# 1. 创建系统组和用户
RUN addgroup --system app && adduser --system --ingroup app app

# 2. 确保 staticfiles 和 media 目录存在，并归属于 app
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app/staticfiles /app/media

# 3. 再将整个 /app 的所有权移交给 app（可选，但建议保留）
RUN chown -R app:app /app

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]