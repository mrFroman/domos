#!/bin/bash

# Скрипт для создания бэкапа всех SQLite баз данных
# Используется перед миграцией на PostgreSQL

set -e

# Директория для бэкапов
BACKUP_DIR="${BACKUP_DIR:-./backups/sqlite}"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"

# Создаем директорию для бэкапа
mkdir -p "$BACKUP_PATH"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Начинаем создание бэкапа SQLite баз..."

# Список SQLite баз для бэкапа
SQLITE_DBS=(
    "web/db.sqlite3"
    "api/advert_tokens.db"
    "api/contract_tokens.db"
    "bot/tgbot/databases/data.db"
    "bot/tgbot/databases/downloaded_audio.db"
    "bot/tgbot/databases/nmarket.db"
    "bot/tgbot/databases/useful_messages.db"
    "bot/tgbot/databases/tradeagent.db"
)

# Копируем каждую базу данных
for db in "${SQLITE_DBS[@]}"; do
    if [ -f "$db" ]; then
        db_name=$(basename "$db")
        db_dir=$(dirname "$db")
        backup_subdir="$BACKUP_PATH/$db_dir"
        mkdir -p "$backup_subdir"
        cp "$db" "$backup_subdir/$db_name"
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Скопирован: $db -> $backup_subdir/$db_name"
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  Файл не найден: $db"
    fi
done

# Копируем .env файлы если есть
if [ -f ".env" ]; then
    cp ".env" "$BACKUP_PATH/.env"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Скопирован: .env"
fi

# Создаем архив
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Создаем архив..."
cd "$BACKUP_DIR"
tar -czf "${TIMESTAMP}.tar.gz" "$TIMESTAMP"
rm -rf "$TIMESTAMP"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Бэкап создан: $BACKUP_DIR/${TIMESTAMP}.tar.gz"

# Показываем размер
FILE_SIZE=$(du -h "$BACKUP_DIR/${TIMESTAMP}.tar.gz" | cut -f1)
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Размер архива: $FILE_SIZE"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Готово!"
