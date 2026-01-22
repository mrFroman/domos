#!/bin/bash
# Скрипт для локального тестирования Docker setup

set -e

echo "🚀 Начало локального тестирования Docker setup"
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    echo "Создайте файл .env на основе .env.example"
    exit 1
fi

echo -e "${GREEN}✅ Файл .env найден${NC}"

# Загружаем переменные окружения
export $(cat .env | grep -v '^#' | xargs)

# Проверка обязательных переменных
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo -e "${RED}❌ POSTGRES_PASSWORD не установлен в .env${NC}"
    exit 1
fi

if [ -z "$BOT_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  BOT_TOKEN не установлен (может быть необязательно для теста)${NC}"
fi

echo -e "${GREEN}✅ Переменные окружения загружены${NC}"
echo ""

# Шаг 1: Остановка существующих контейнеров
echo "📦 Шаг 1: Остановка существующих контейнеров..."
docker-compose down -v 2>/dev/null || true
echo -e "${GREEN}✅ Готово${NC}"
echo ""

# Шаг 2: Запуск PostgreSQL
echo "🐘 Шаг 2: Запуск PostgreSQL контейнера..."
docker-compose up -d postgres

# Ждем пока PostgreSQL станет готов
echo "⏳ Ожидание готовности PostgreSQL..."
timeout=60
counter=0
while ! docker-compose exec -T postgres pg_isready -U ${POSTGRES_USER:-domos} > /dev/null 2>&1; do
    sleep 2
    counter=$((counter + 2))
    if [ $counter -ge $timeout ]; then
        echo -e "${RED}❌ PostgreSQL не запустился за $timeout секунд${NC}"
        docker-compose logs postgres
        exit 1
    fi
    echo -n "."
done
echo ""
echo -e "${GREEN}✅ PostgreSQL готов!${NC}"
echo ""

# Шаг 3: Проверка подключения
echo "🔌 Шаг 3: Проверка подключения к БД..."
python3 scripts/test_connection.py
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибка подключения к БД${NC}"
    exit 1
fi
echo ""

# Шаг 4: Проверка схем
echo "📋 Шаг 4: Проверка создания схем..."
docker-compose exec -T postgres psql -U ${POSTGRES_USER:-domos} -d ${POSTGRES_DB:-domos} -c "\dn" | grep -E "(main|advert|contract|django|bot)" || {
    echo -e "${RED}❌ Схемы не созданы${NC}"
    exit 1
}
echo -e "${GREEN}✅ Схемы созданы${NC}"
echo ""

# Шаг 5: Список SQLite баз для миграции
echo "📁 Шаг 5: Поиск SQLite баз для миграции..."
SQLITE_DBS=()

if [ -f "bot/tgbot/databases/data.db" ]; then
    SQLITE_DBS+=("bot/tgbot/databases/data.db:main")
    echo "   ✅ Найдена: bot/tgbot/databases/data.db (main)"
fi

if [ -f "api/advert_tokens.db" ]; then
    SQLITE_DBS+=("api/advert_tokens.db:advert")
    echo "   ✅ Найдена: api/advert_tokens.db (advert)"
fi

if [ -f "api/contract_tokens.db" ]; then
    SQLITE_DBS+=("api/contract_tokens.db:contract")
    echo "   ✅ Найдена: api/contract_tokens.db (contract)"
fi

if [ -f "web/db.sqlite3" ]; then
    SQLITE_DBS+=("web/db.sqlite3:django")
    echo "   ✅ Найдена: web/db.sqlite3 (django)"
fi

if [ ${#SQLITE_DBS[@]} -eq 0 ]; then
    echo -e "${YELLOW}⚠️  SQLite базы не найдены. Пропускаем миграцию данных.${NC}"
    echo ""
    echo "💡 Для создания тестовых данных можно:"
    echo "   1. Запустить приложение с SQLite (DB_TYPE=sqlite)"
    echo "   2. Создать тестовые данные"
    echo "   3. Затем мигрировать их в PostgreSQL"
else
    echo ""
    echo "🔄 Шаг 6: Миграция данных из SQLite в PostgreSQL..."
    
    # Формируем URL для подключения к PostgreSQL
    # Используем localhost для подключения с хоста
    POSTGRES_URL="postgresql://${POSTGRES_USER:-domos}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-domos}"
    
    echo "   URL подключения: postgresql://${POSTGRES_USER:-domos}:***@localhost:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-domos}"
    echo ""
    
    for db_info in "${SQLITE_DBS[@]}"; do
        IFS=':' read -r sqlite_path schema <<< "$db_info"
        echo "   📦 Миграция: $sqlite_path -> схема '$schema'"
        
        if [ ! -f "$sqlite_path" ]; then
            echo -e "   ${YELLOW}⚠️  Файл не найден: $sqlite_path${NC}"
            continue
        fi
        
        python3 scripts/migrate_sqlite_to_postgres.py \
            --postgres-url "$POSTGRES_URL" \
            --sqlite-path "$sqlite_path" \
            --schema "$schema"
        
        if [ $? -eq 0 ]; then
            echo -e "   ${GREEN}✅ Успешно${NC}"
        else
            echo -e "   ${RED}❌ Ошибка миграции${NC}"
            echo ""
            echo "💡 Попробуйте выполнить миграцию вручную:"
            echo "   python3 scripts/migrate_sqlite_to_postgres.py \\"
            echo "     --postgres-url \"$POSTGRES_URL\" \\"
            echo "     --sqlite-path \"$sqlite_path\" \\"
            echo "     --schema \"$schema\""
            exit 1
        fi
    done
    
    echo ""
    echo "📊 Проверка мигрированных данных..."
    docker-compose exec -T postgres psql -U ${POSTGRES_USER:-domos} -d ${POSTGRES_DB:-domos} -c "
    SELECT 
        schemaname,
        COUNT(*) as table_count,
        SUM(n_live_tup) as total_rows
    FROM pg_stat_user_tables
    WHERE schemaname IN ('main', 'advert', 'contract', 'django')
    GROUP BY schemaname
    ORDER BY schemaname;
    " 2>/dev/null || echo "   (Не удалось получить статистику)"
fi

echo ""
echo -e "${GREEN}✅ Все тесты пройдены успешно!${NC}"
echo ""
echo "📝 Следующие шаги:"
echo "   1. Запустить все сервисы: docker-compose up"
echo "   2. Проверить логи: docker-compose logs -f"
echo "   3. Остановить: docker-compose down"
echo ""
