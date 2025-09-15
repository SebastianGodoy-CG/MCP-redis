# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# copiar e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copiar el código
COPY . .

# Puerto que expone la app
ENV PORT=8000

# CMD usando Gunicorn + Uvicorn workers (2 workers; ajusta según CPU/memoria)
CMD ["gunicorn","main:app"]
