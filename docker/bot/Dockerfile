FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    libpq-dev \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Установка браузеров для Playwright
RUN playwright install --with-deps chromium || true

# Копируем код приложения
COPY . .

# Устанавливаем PYTHONPATH для доступа к модулям (web, bot, config)
ENV PYTHONPATH=/app:$PYTHONPATH

# Удаляем конфликтующий пакет config из PyPI, если он установлен
RUN pip uninstall -y config 2>/dev/null || true

# Создаем директории для данных бота
RUN mkdir -p /app/bot/tgbot/databases \
    /app/bot/tgbot/vector_index \
    /app/images \
    /app/logs

# Порт не нужен для бота (он работает через Telegram API)
EXPOSE 8080

# Команда запуска (переопределяется в docker-compose.yml)
CMD ["python", "-m", "bot.bot"]
