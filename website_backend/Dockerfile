# website_backend/Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app_realtime_website.py .
COPY templates/ ./templates/

CMD ["python", "app_realtime_website.py"]