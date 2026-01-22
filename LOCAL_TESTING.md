# Инструкция по локальному тестированию Docker и PostgreSQL

## Подготовка

### 1. Установка зависимостей

```bash
# Установить Docker и Docker Compose (если еще не установлены)
# macOS:
brew install docker docker-compose

# Linux:
sudo apt-get update
sudo apt-get install docker.io docker-compose
```

### 2. Создание файла .env

Создайте файл `.env` в корне проекта:

```bash
# Скопируйте пример (если есть)
cp .env.example .env

# Или создайте вручную с минимальными настройками:
cat > .env << EOF
# PostgreSQL
POSTGRES_DB=domos
POSTGRES_USER=domos
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_PORT=5432
POSTGRES_HOST=localhost

# Database Type
DB_TYPE=postgres

# Service Ports
API_PORT=8001
WEB_PORT=8002
BOT_API_PORT=6000

# Telegram Bot (обязательно для запуска бота)
BOT_TOKEN=your_telegram_bot_token_here

# Timezone
TZ=Europe/Moscow
EOF
```

**⚠️ ВАЖНО:** Замените `your_secure_password_here` на реальный пароль!

## Быстрый тест (автоматический)

Запустите автоматический скрипт тестирования:

```bash
./scripts/test_local_setup.sh
```

Этот скрипт:
1. ✅ Проверит наличие .env файла
2. ✅ Остановит существующие контейнеры
3. ✅ Запустит PostgreSQL
4. ✅ Проверит подключение к БД
5. ✅ Проверит создание схем
6. ✅ Мигрирует данные из SQLite (если есть)

## Ручное тестирование (пошагово)

### Шаг 1: Запуск PostgreSQL

```bash
# Запустить только PostgreSQL контейнер
docker-compose up -d postgres

# Проверить статус
docker-compose ps

# Посмотреть логи
docker-compose logs postgres
```

### Шаг 2: Проверка подключения

```bash
# Запустить скрипт проверки подключения
python3 scripts/test_connection.py
```

Ожидаемый вывод:
```
🔌 Подключение к PostgreSQL...
   Host: localhost
   Port: 5432
   Database: domos
   User: domos
✅ Подключение успешно!

📋 Найденные схемы:
   - advert
   - bot
   - contract
   - django
   - main
```

### Шаг 3: Проверка схем вручную

```bash
# Подключиться к PostgreSQL через psql
docker-compose exec postgres psql -U domos -d domos

# В psql выполнить:
\dn          # Список схем
\dt main.*   # Таблицы в схеме main
\q           # Выход
```

### Шаг 4: Миграция данных

Если у вас есть SQLite базы, мигрируйте их:

```bash
# Установить зависимости (если еще не установлены)
pip install psycopg2-binary python-dotenv

# Миграция основной БД
python3 scripts/migrate_sqlite_to_postgres.py \
  --postgres-url "postgresql://domos:your_password@localhost:5432/domos" \
  --sqlite-path "bot/tgbot/databases/data.db" \
  --schema "main"

# Миграция БД рекламы
python3 scripts/migrate_sqlite_to_postgres.py \
  --postgres-url "postgresql://domos:your_password@localhost:5432/domos" \
  --sqlite-path "api/advert_tokens.db" \
  --schema "advert"

# Миграция БД контрактов
python3 scripts/migrate_sqlite_to_postgres.py \
  --postgres-url "postgresql://domos:your_password@localhost:5432/domos" \
  --sqlite-path "api/contract_tokens.db" \
  --schema "contract"

# Миграция Django БД
python3 scripts/migrate_sqlite_to_postgres.py \
  --postgres-url "postgresql://domos:your_password@localhost:5432/domos" \
  --sqlite-path "web/db.sqlite3" \
  --schema "django"
```

### Шаг 5: Проверка миграции данных

```bash
# Проверить количество записей в таблицах
docker-compose exec postgres psql -U domos -d domos -c "
SELECT 
    schemaname,
    tablename,
    n_live_tup as row_count
FROM pg_stat_user_tables
WHERE schemaname IN ('main', 'advert', 'contract', 'django')
ORDER BY schemaname, tablename;
"
```

### Шаг 6: Тестирование сервисов

```bash
# Запустить все сервисы (в фоне)
docker-compose up -d

# Или в режиме просмотра логов
docker-compose up

# Проверить статус всех контейнеров
docker-compose ps

# Посмотреть логи конкретного сервиса
docker-compose logs -f api
docker-compose logs -f web
docker-compose logs -f bot
```

### Шаг 7: Проверка работы API

```bash
# Проверить доступность API
curl http://localhost:8001/docs

# Проверить доступность Web
curl http://localhost:8002
```

## Остановка и очистка

```bash
# Остановить все контейнеры
docker-compose down

# Остановить и удалить volumes (⚠️ удалит все данные!)
docker-compose down -v

# Остановить только PostgreSQL
docker-compose stop postgres
```

## Решение проблем

### Проблема: PostgreSQL не запускается

```bash
# Проверить логи
docker-compose logs postgres

# Проверить, не занят ли порт 5432
lsof -i :5432

# Если порт занят, измените POSTGRES_PORT в .env
```

### Проблема: Ошибка подключения

1. Проверьте, что PostgreSQL контейнер запущен:
   ```bash
   docker-compose ps
   ```

2. Проверьте переменные окружения:
   ```bash
   docker-compose exec postgres env | grep POSTGRES
   ```

3. Проверьте пароль в .env файле

### Проблема: Схемы не созданы

```bash
# Выполнить init_db.sql вручную
docker-compose exec postgres psql -U domos -d domos -f /docker-entrypoint-initdb.d/init.sql
```

### Проблема: Ошибка миграции данных

1. Проверьте, что SQLite файлы существуют:
   ```bash
   ls -la bot/tgbot/databases/data.db
   ls -la api/advert_tokens.db
   ```

2. Проверьте права доступа к файлам

3. Проверьте формат URL PostgreSQL:
   ```bash
   # Правильный формат:
   postgresql://user:password@host:port/database
   ```

## Подготовка к развертыванию на сервере

После успешного локального тестирования:

1. **Создайте бэкап SQLite баз:**
   ```bash
   ./scripts/backup_sqlite.sh
   ```

2. **Экспортируйте данные PostgreSQL (опционально):**
   ```bash
   docker-compose exec postgres pg_dump -U domos domos > backup_postgres.sql
   ```

3. **На сервере выполните те же шаги:**
   - Скопируйте проект
   - Создайте .env файл
   - Запустите `./scripts/test_local_setup.sh`
   - Или выполните шаги вручную

## Проверочный чеклист

Перед развертыванием на сервере убедитесь:

- [ ] PostgreSQL контейнер запускается
- [ ] Подключение к БД работает
- [ ] Все схемы созданы (main, advert, contract, django, bot)
- [ ] Данные мигрированы (если были SQLite базы)
- [ ] API сервис запускается
- [ ] Web сервис запускается
- [ ] Bot сервис запускается (если есть BOT_TOKEN)
- [ ] Все переменные окружения установлены

## Дополнительная информация

- Логи всех сервисов: `docker-compose logs -f`
- Статус контейнеров: `docker-compose ps`
- Перезапуск сервиса: `docker-compose restart api`
- Просмотр использования ресурсов: `docker stats`
