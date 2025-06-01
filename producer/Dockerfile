# producer/Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

COPY producer.py .

CMD ["python", "producer.py"]