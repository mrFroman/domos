FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем зависимости
COPY requirements-api.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Копируем код приложения
COPY . .

# Устанавливаем PYTHONPATH для доступа к модулям (bot, config)
ENV PYTHONPATH=/app:$PYTHONPATH

# Создаем директории для логов и данных
RUN mkdir -p /app/logs /app/data

# Порт для FastAPI
EXPOSE 8001

# Команда запуска (переопределяется в docker-compose.yml)
CMD ["python", "-m", "api.main"]
