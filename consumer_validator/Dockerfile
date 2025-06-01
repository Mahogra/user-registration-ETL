# consumer_validator/Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY consumer_validator.py .

CMD ["python", "consumer_validator.py"]