# Инструкция по развертыванию на сервере

## Подготовка на сервере

### 1. Установка Docker и Docker Compose

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# Добавить пользователя в группу docker (чтобы не использовать sudo)
sudo usermod -aG docker $USER
# Выйти и войти снова для применения изменений
```

### 2. Клонирование проекта

```bash
# Перейти в рабочую директорию
cd /path/to/your/projects

# Клонировать репозиторий (или скопировать файлы)
git clone <your-repo-url> domos
cd domos

# Переключиться на ветку миграции
git checkout feature/docker-postgres-migration
```

### 3. Создание .env файла

```bash
# Создать .env файл с настройками для продакшена
nano .env
```

Минимальный набор переменных:

```bash
# PostgreSQL
POSTGRES_DB=domos
POSTGRES_USER=domos
POSTGRES_PASSWORD=your_very_secure_password_here
POSTGRES_PORT=5432
POSTGRES_HOST=postgres

# Database Type
DB_TYPE=postgres

# Service Ports
API_PORT=8001
WEB_PORT=8002
BOT_API_PORT=6000

# Telegram Bot
BOT_TOKEN=your_production_bot_token

# Timezone
TZ=Europe/Moscow

# Другие необходимые переменные из вашего .env
```

## Развертывание

### Вариант 1: Автоматический (рекомендуется)

```bash
# Запустить автоматический скрипт тестирования и миграции
./scripts/test_local_setup.sh
```

Этот скрипт:
- ✅ Проверит настройки
- ✅ Запустит PostgreSQL
- ✅ Создаст схемы
- ✅ Мигрирует данные из SQLite (если есть)

### Вариант 2: Ручной (пошагово)

#### Шаг 1: Бэкап существующих данных

```bash
# Если есть SQLite базы, создайте бэкап
./scripts/backup_sqlite.sh

# Сохраните бэкапы в безопасное место
cp -r scripts/backups /backup/location/
```

#### Шаг 2: Запуск PostgreSQL

```bash
# Запустить только PostgreSQL
docker-compose up -d postgres

# Дождаться готовности (проверить логи)
docker-compose logs -f postgres
# Нажать Ctrl+C когда увидите "database system is ready to accept connections"
```

#### Шаг 3: Проверка подключения

```bash
# Проверить подключение
python3 scripts/test_connection.py
```

#### Шаг 4: Миграция данных

Если у вас есть SQLite базы на сервере:

```bash
# Установить зависимости (если нужно)
pip3 install psycopg2-binary python-dotenv

# Миграция каждой базы
POSTGRES_URL="postgresql://domos:your_password@localhost:5432/domos"

python3 scripts/migrate_sqlite_to_postgres.py \
  --postgres-url "$POSTGRES_URL" \
  --sqlite-path "bot/tgbot/databases/data.db" \
  --schema "main"

python3 scripts/migrate_sqlite_to_postgres.py \
  --postgres-url "$POSTGRES_URL" \
  --sqlite-path "api/advert_tokens.db" \
  --schema "advert"

python3 scripts/migrate_sqlite_to_postgres.py \
  --postgres-url "$POSTGRES_URL" \
  --sqlite-path "api/contract_tokens.db" \
  --schema "contract"

python3 scripts/migrate_sqlite_to_postgres.py \
  --postgres-url "$POSTGRES_URL" \
  --sqlite-path "web/db.sqlite3" \
  --schema "django"
```

#### Шаг 5: Запуск всех сервисов

```bash
# Запустить все сервисы
docker-compose up -d

# Проверить статус
docker-compose ps

# Посмотреть логи
docker-compose logs -f
```

## Настройка Nginx (если используется)

Обновите конфигурацию Nginx для проксирования на Docker контейнеры:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # FastAPI на порту 8001
    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Django на порту 8002
    location /domosclub/ {
        proxy_pass http://localhost:8002/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Статические файлы Django
    location /domosclub/static/ {
        alias /path/to/domos/web/static/;
    }
}
```

Перезагрузите Nginx:

```bash
sudo nginx -t  # Проверка конфигурации
sudo systemctl reload nginx
```

## Мониторинг и обслуживание

### Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f api
docker-compose logs -f bot
docker-compose logs -f postgres
```

### Перезапуск сервисов

```bash
# Перезапустить все
docker-compose restart

# Перезапустить конкретный сервис
docker-compose restart api
```

### Бэкапы PostgreSQL

Бэкапы создаются автоматически каждый день в 3:00 по московскому времени.

Ручной бэкап:

```bash
# Через контейнер бэкапа
docker exec domos_postgres_backup /backup_postgres.sh

# Или напрямую
docker-compose exec postgres pg_dump -U domos domos > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Восстановление из бэкапа

```bash
# Восстановить из файла
docker-compose exec -T postgres psql -U domos domos < backup_file.sql

# Или использовать скрипт
./scripts/restore_postgres.sh backup_file.sql
```

## Откат к SQLite (если нужно)

Если что-то пошло не так, можно быстро вернуться к SQLite:

1. Остановить Docker контейнеры:
   ```bash
   docker-compose down
   ```

2. Изменить DB_TYPE в .env:
   ```bash
   DB_TYPE=sqlite
   ```

3. Запустить сервисы как обычно (без Docker)

## Проверка после развертывания

- [ ] PostgreSQL контейнер запущен и работает
- [ ] Все схемы созданы
- [ ] Данные мигрированы (проверить количество записей)
- [ ] API доступен (curl http://localhost:8001/docs)
- [ ] Web доступен (curl http://localhost:8002)
- [ ] Bot работает (проверить логи)
- [ ] Бэкапы создаются автоматически
- [ ] Nginx проксирует запросы правильно

## Решение проблем

### Проблема: Контейнеры не запускаются

```bash
# Проверить логи
docker-compose logs

# Проверить использование портов
sudo netstat -tulpn | grep -E ':(8001|8002|5432|6000)'

# Проверить права доступа
ls -la docker-compose.yml
```

### Проблема: Ошибка подключения к БД

1. Проверить, что PostgreSQL запущен:
   ```bash
   docker-compose ps postgres
   ```

2. Проверить переменные окружения:
   ```bash
   docker-compose exec postgres env | grep POSTGRES
   ```

3. Проверить подключение вручную:
   ```bash
   docker-compose exec postgres psql -U domos -d domos
   ```

### Проблема: Данные не мигрированы

1. Проверить наличие SQLite файлов
2. Проверить права доступа
3. Выполнить миграцию вручную с подробным выводом

## Обновление

При обновлении кода:

```bash
# Остановить сервисы
docker-compose down

# Обновить код
git pull

# Пересобрать образы (если изменились Dockerfile)
docker-compose build

# Запустить снова
docker-compose up -d
```

## Безопасность

- ✅ Используйте сильные пароли для PostgreSQL
- ✅ Ограничьте доступ к портам (firewall)
- ✅ Регулярно обновляйте Docker образы
- ✅ Храните .env файл в безопасности (не коммитьте в Git)
- ✅ Настройте регулярные бэкапы
