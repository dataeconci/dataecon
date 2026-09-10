FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

EXPOSE 10000

CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--chdir", "app", "--timeout", "120", "app:app"]