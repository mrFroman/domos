# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей и устанавливаем их
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект в контейнер
COPY . .

# Экспортируем порт, на котором будет работать Django
EXPOSE 8002

# Команда по умолчанию для запуска сервера
CMD ["python", "manage.py", "runserver", "0.0.0.0:8002"]
