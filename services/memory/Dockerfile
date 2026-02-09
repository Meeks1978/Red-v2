FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations

ENV RED_MEMORY_DB=/data/red_memory.sqlite
ENV RED_MEMORY_MIGRATION=/app/migrations/001_init.sql

EXPOSE 8092

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8092"]
