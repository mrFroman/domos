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

# Устанавливаем PYTHONPATH для доступа к модулям (web, bot, config)
ENV PYTHONPATH=/app:$PYTHONPATH

# Удаляем конфликтующий пакет config из PyPI, если он установлен
RUN pip uninstall -y config 2>/dev/null || true

# Создаем директории для логов
RUN mkdir -p /app/logs

# Порт для Flask API
EXPOSE 6000

# Команда запуска (переопределяется в docker-compose.yml)
CMD ["python", "-m", "bot.main"]
