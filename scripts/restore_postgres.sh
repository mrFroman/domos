#!/bin/bash

# Скрипт для восстановления PostgreSQL из бэкапа

set -e

# Переменные окружения
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-domos}"
POSTGRES_USER="${POSTGRES_USER:-domos}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"

# Директория с бэкапами
BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"

# Проверяем аргументы
if [ -z "$1" ]; then
    echo "Использование: $0 <путь_к_бэкапу>"
    echo ""
    echo "Доступные бэкапы:"
    ls -lh "$BACKUP_DIR"/domos_*.sql.gz 2>/dev/null | tail -10 || echo "Бэкапы не найдены"
    exit 1
fi

BACKUP_FILE="$1"

# Проверяем существование файла
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Файл бэкапа не найден: $BACKUP_FILE"
    exit 1
fi

# Экспортируем пароль для pg_restore
export PGPASSWORD="$POSTGRES_PASSWORD"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  ВНИМАНИЕ: Вы собираетесь восстановить базу данных из бэкапа!"
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Бэкап: $BACKUP_FILE"
echo "[$(date +'%Y-%m-%d %H:%M:%S')] База данных: $POSTGRES_DB на $POSTGRES_HOST:$POSTGRES_PORT"
echo ""
read -p "Это действие перезапишет текущую базу данных. Продолжить? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Восстановление отменено."
    exit 0
fi

# Создаем бэкап текущей БД перед восстановлением
CURRENT_BACKUP="$BACKUP_DIR/pre_restore_$(date +'%Y-%m-%d_%H-%M-%S').sql.gz"
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Создаем бэкап текущей БД перед восстановлением: $CURRENT_BACKUP"
pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --format=custom \
    --compress=9 \
    --file="$CURRENT_BACKUP" \
    --verbose

# Восстанавливаем из бэкапа
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Начинаем восстановление из бэкапа..."
pg_restore -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --clean \
    --if-exists \
    --verbose \
    "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ База данных успешно восстановлена из бэкапа!"
else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ❌ Ошибка при восстановлении базы данных!"
    exit 1
fi
