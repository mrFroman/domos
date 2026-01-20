# Статус миграции на Docker Compose и PostgreSQL

## ✅ Выполнено

### Этап 1: Подготовка
- [x] Создан общий `requirements.txt` со всеми зависимостями
- [x] Создан скрипт бэкапа SQLite баз (`scripts/backup_sqlite.sh`)
- [x] Создана структура папок для Docker (`docker/api`, `docker/web`, `docker/bot`, `docker/bot-api`)

### Этап 2: Docker инфраструктура
- [x] Создан `docker-compose.yml` с сервисами:
  - PostgreSQL с автоматическими бэкапами
  - API (FastAPI)
  - Web (Django)
  - Bot (aiogram)
  - Bot-API (Flask)
- [x] Созданы Dockerfile для каждого сервиса
- [x] Настроен PostgreSQL с healthcheck
- [x] Настроены volumes для данных
- [x] Настроен networking между сервисами

### Этап 3: Абстракция БД
- [x] Создан `config.py` с поддержкой обеих БД через `DB_TYPE`
- [x] Создан модуль `bot/tgbot/databases/database.py` с абстракцией:
  - Класс `DatabaseConnection` для работы с SQLite и PostgreSQL
  - Автоматическая адаптация SQL запросов (? -> %s)
  - Функции-обертки для удобства использования

### Этап 4: Миграция схемы
- [x] Создан скрипт `scripts/migrate_sqlite_to_postgres.py`:
  - Чтение схемы из SQLite
  - Создание таблиц в PostgreSQL
  - Копирование данных
  - Поддержка разных схем (main, advert, contract, django, bot)

### Этап 5: Обновление кода
- [x] Обновлен `web/web/settings.py` для поддержки PostgreSQL
- [ ] Обновление всех `sqlite3.connect` на новую абстракцию (в процессе)
- [ ] Обновление всех `aiosqlite.connect` на новую абстракцию (в процессе)

## 📋 Следующие шаги

### 1. Обновление кода для использования database.py
Нужно заменить все прямые вызовы `sqlite3.connect` и `aiosqlite.connect` на использование `database.py`:

**Пример замены:**
```python
# Было:
import sqlite3
conn = sqlite3.connect(MAIN_DB_PATH)
cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# Стало:
from bot.tgbot.databases.database import DatabaseConnection
db = DatabaseConnection(MAIN_DB_PATH, schema="main")
result = db.fetchone("SELECT * FROM users WHERE id = %s", (user_id,))
```

### 2. Миграция данных
После обновления кода нужно выполнить миграцию данных:

```bash
# 1. Создать бэкап SQLite баз
./scripts/backup_sqlite.sh

# 2. Запустить PostgreSQL в Docker
docker-compose up -d postgres

# 3. Мигрировать каждую базу в свою схему
python scripts/migrate_sqlite_to_postgres.py \
  --postgres-url "postgresql://domos:password@localhost:5432/domos" \
  --sqlite-path "bot/tgbot/databases/data.db" \
  --schema "main"

python scripts/migrate_sqlite_to_postgres.py \
  --postgres-url "postgresql://domos:password@localhost:5432/domos" \
  --sqlite-path "api/advert_tokens.db" \
  --schema "advert"

python scripts/migrate_sqlite_to_postgres.py \
  --postgres-url "postgresql://domos:password@localhost:5432/domos" \
  --sqlite-path "api/contract_tokens.db" \
  --schema "contract"

python scripts/migrate_sqlite_to_postgres.py \
  --postgres-url "postgresql://domos:password@localhost:5432/domos" \
  --sqlite-path "web/db.sqlite3" \
  --schema "django"
```

### 3. Тестирование
- [ ] Локальное тестирование в Docker
- [ ] Проверка всех функций
- [ ] Нагрузочное тестирование

### 4. Развертывание
- [ ] Развертывание на staging
- [ ] Миграция production данных
- [ ] Переключение nginx
- [ ] Мониторинг работы

## 📁 Структура файлов

```
domos/
├── docker-compose.yml          # Docker Compose конфигурация
├── requirements.txt            # Общие зависимости
├── config.py                   # Конфигурация с поддержкой обеих БД
├── docker/
│   ├── api/Dockerfile
│   ├── web/Dockerfile
│   ├── bot/Dockerfile
│   └── bot-api/Dockerfile
├── scripts/
│   ├── backup_sqlite.sh         # Бэкап SQLite баз
│   ├── backup_postgres.sh       # Бэкап PostgreSQL
│   ├── restore_postgres.sh      # Восстановление из бэкапа
│   ├── migrate_sqlite_to_postgres.py  # Миграция данных
│   └── init_db.sql              # Инициализация PostgreSQL
└── bot/tgbot/databases/
    └── database.py              # Абстракция для работы с БД
```

## 🔧 Переменные окружения

Создайте файл `.env.docker` (или используйте существующий `.env`):

```bash
# PostgreSQL
POSTGRES_DB=domos
POSTGRES_USER=domos
POSTGRES_PASSWORD=your_secure_password
POSTGRES_PORT=5432

# Тип БД (sqlite или postgres)
DB_TYPE=postgres

# Порты сервисов
API_PORT=8001
WEB_PORT=8002
BOT_API_PORT=6000

# Telegram Bot Token
BOT_TOKEN=your_bot_token

# Часовой пояс
TZ=Europe/Moscow
```

## 🚀 Запуск

### Локальная разработка (SQLite)
```bash
# Установить зависимости
pip install -r requirements.txt

# Запустить сервисы как обычно
python api/main.py
python web/manage.py runserver 0.0.0.0:8002
python bot/bot.py
```

### Docker (PostgreSQL)
```bash
# Запустить все сервисы
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановить
docker-compose down
```

## ⚠️ Важные замечания

1. **Переменная DB_TYPE**: Используется для переключения между SQLite и PostgreSQL без изменения кода
2. **Схемы PostgreSQL**: Разные сервисы используют разные схемы для изоляции данных
3. **Бэкапы**: Автоматические бэкапы PostgreSQL создаются каждый день в 3:00
4. **Откат**: Всегда можно вернуться к SQLite, установив `DB_TYPE=sqlite`

## 📝 Заметки

- Все изменения в отдельной ветке (если используется Git)
- SQLite базы остаются на месте и работают параллельно
- Миграция данных выполняется один раз перед переходом на PostgreSQL
