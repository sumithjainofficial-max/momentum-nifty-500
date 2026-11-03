# Production Cloud Run Container for NIFTY 500 Momentum Desk
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=True
ENV PORT=8080
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app

