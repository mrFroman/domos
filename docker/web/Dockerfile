FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаем директории для статики и медиа
RUN mkdir -p /app/static /app/media /app/logs

# Порт для Django
EXPOSE 8002

# Команда запуска (переопределяется в docker-compose.yml)
CMD ["python", "web/manage.py", "runserver", "0.0.0.0:8002"]
