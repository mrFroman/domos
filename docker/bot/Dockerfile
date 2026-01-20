FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаем директории для данных бота
RUN mkdir -p /app/bot/tgbot/databases \
    /app/bot/tgbot/vector_index \
    /app/images \
    /app/logs

# Порт не нужен для бота (он работает через Telegram API)
EXPOSE 8080

# Команда запуска (переопределяется в docker-compose.yml)
CMD ["python", "bot/bot.py"]
