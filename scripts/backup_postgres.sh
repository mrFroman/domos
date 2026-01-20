#!/bin/bash

# Скрипт для автоматического бэкапа PostgreSQL
# Создает бэкап каждый день и удаляет бэкапы старше 7 дней
# Можно использовать Python версию (backup_postgres.py) или эту bash версию

set -e

# Переменные окружения
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-domos}"
POSTGRES_USER="${POSTGRES_USER:-domos}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"
BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Проверяем наличие пароля
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ❌ Ошибка: POSTGRES_PASSWORD не установлен"
    exit 1
fi

# Создаем директорию для бэкапов если её нет
mkdir -p "$BACKUP_DIR"

# Формат имени файла: domos_YYYY-MM-DD_HH-MM-SS.sql.gz
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="$BACKUP_DIR/domos_${TIMESTAMP}.sql.gz"

# Экспортируем пароль для pg_dump
export PGPASSWORD="$POSTGRES_PASSWORD"

# Создаем бэкап
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Начинаем создание бэкапа PostgreSQL..."
echo "[$(date +'%Y-%m-%d %H:%M:%S')] База: $POSTGRES_DB, Хост: $POSTGRES_HOST:$POSTGRES_PORT"

pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --format=custom \
    --compress=9 \
    --file="$BACKUP_FILE" \
    --verbose

if [ $? -eq 0 ]; then
    # Получаем размер файла
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Бэкап успешно создан: $BACKUP_FILE"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Размер бэкапа: $FILE_SIZE"
else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ❌ Ошибка при создании бэкапа!"
    exit 1
fi

# Удаляем бэкапы старше RETENTION_DAYS дней
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Удаляем бэкапы старше $RETENTION_DAYS дней..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "domos_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)

if [ $DELETED_COUNT -gt 0 ]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Удалено старых бэкапов: $DELETED_COUNT"
else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Старые бэкапы не найдены"
fi

# Показываем список текущих бэкапов
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Текущие бэкапы (последние 7):"
ls -lh "$BACKUP_DIR"/domos_*.sql.gz 2>/dev/null | tail -7 | awk '{print "  - " $9 " (" $5 ")"}' || echo "  Бэкапы не найдены"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Готово!"
