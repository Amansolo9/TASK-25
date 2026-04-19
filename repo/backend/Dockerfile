FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN sed -i 's/\r$//' /app/entrypoint.sh /app/scripts/nightly_backup_loop.sh /app/scripts/offline_ingest_worker_loop.sh \
    && chmod +x /app/entrypoint.sh /app/scripts/nightly_backup_loop.sh /app/scripts/offline_ingest_worker_loop.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
