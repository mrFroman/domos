# План миграции на Docker Compose и PostgreSQL

## Текущее состояние

### Сервисы:
1. **API** (FastAPI) - порт 8001, запуск: `python api/main.py`
2. **Web** (Django) - порт 8002, запуск: `python web/manage.py runserver 0.0.0.0:8002`
3. **Bot** (aiogram) - запуск: `python bot/bot.py`
4. **Bot API** (Flask) - порт 6000, запуск: `python bot/main.py`

### SQLite базы данных:
1. `web/db.sqlite3` - Django БД
2. `api/advert_tokens.db` - токены рекламы (ADVERT_TOKENS_DB_PATH)
3. `api/contract_tokens.db` - токены контрактов (CONTRACT_TOKENS_DB_PATH)
4. `bot/tgbot/databases/data.db` - основная БД (MAIN_DB_PATH)
5. `bot/tgbot/databases/downloaded_audio.db` - аудио файлы
6. `bot/tgbot/databases/nmarket.db` - парсинг nmarket
7. `bot/tgbot/databases/useful_messages.db` - полезные сообщения
8. `bot/tgbot/databases/tradeagent.db` - парсинг tradeagent

### Мониторинги (запускаются через Popen):
- tsmonitor
- payment_monitor
- notifymonitor
- eventsmonitor
- ban_monitor
- monthly_anket
- recurrent_payments
- parse_messages

---

## Стратегия миграции

### Фаза 1: Подготовка (без изменений в коде)

#### 1.1 Создание ветки для миграции
```bash
git checkout -b feature/docker-postgres-migration
```

#### 1.2 Анализ зависимостей
- Собрать все requirements.txt
- Определить версии Python
- Проверить совместимость библиотек

#### 1.3 Резервное копирование
- Создать полный бэкап всех SQLite баз
- Сохранить текущие .env файлы
- Документировать текущие настройки

---

### Фаза 2: Создание Docker инфраструктуры (параллельно с текущей системой)

#### 2.1 Структура Docker Compose
```
domos/
├── docker-compose.yml          # Основной файл
├── docker-compose.override.yml  # Локальные переопределения (в .gitignore)
├── .env.docker                  # Переменные окружения для Docker
├── docker/
│   ├── api/
│   │   └── Dockerfile
│   ├── web/
│   │   └── Dockerfile
│   ├── bot/
│   │   └── Dockerfile
│   └── bot-api/
│       └── Dockerfile
└── scripts/
    ├── migrate_sqlite_to_postgres.py
    └── backup_sqlite.sh
```

#### 2.2 Docker Compose структура
```yaml
services:
  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      POSTGRES_DB: domos
      POSTGRES_USER: domos
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U domos"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: docker/api/Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://domos:${POSTGRES_PASSWORD}@postgres:5432/domos
      - MAIN_DB_PATH=postgresql://domos:${POSTGRES_PASSWORD}@postgres:5432/domos
      - ADVERT_TOKENS_DB_PATH=postgresql://domos:${POSTGRES_PASSWORD}@postgres:5432/domos
      - CONTRACT_TOKENS_DB_PATH=postgresql://domos:${POSTGRES_PASSWORD}@postgres:5432/domos
    ports:
      - "8001:8001"
    volumes:
      - ./api:/app/api
      - ./bot:/app/bot
      - ./config.py:/app/config.py
    command: python api/main.py

  web:
    build:
      context: .
      dockerfile: docker/web/Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://domos:${POSTGRES_PASSWORD}@postgres:5432/domos
    ports:
      - "8002:8002"
    volumes:
      - ./web:/app/web
    command: python web/manage.py runserver 0.0.0.0:8002

  bot:
    build:
      context: .
      dockerfile: docker/bot/Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://domos:${POSTGRES_PASSWORD}@postgres:5432/domos
      - MAIN_DB_PATH=postgresql://domos:${POSTGRES_PASSWORD}@postgres:5432/domos
    volumes:
      - ./bot:/app/bot
      - ./config.py:/app/config.py
      - ./images:/app/images
    command: python bot/bot.py

  bot-api:
    build:
      context: .
      dockerfile: docker/bot-api/Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://domos:${POSTGRES_PASSWORD}@postgres:5432/domos
    ports:
      - "6000:6000"
    volumes:
      - ./bot:/app/bot
    command: python bot/main.py

volumes:
  postgres_data:
```

---

### Фаза 3: Создание абстракции доступа к БД (без изменения логики)

#### 3.1 Создание модуля database.py
```python
# bot/tgbot/databases/database.py
import os
from typing import Union
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

# Определяем тип БД из переменной окружения
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # sqlite или postgres

class DatabaseConnection:
    """Абстракция для работы с SQLite и PostgreSQL"""
    
    def __init__(self, db_path_or_url: str):
        self.db_path_or_url = db_path_or_url
        self.db_type = DB_TYPE
        
    def connect(self):
        if self.db_type == "postgres":
            return psycopg2.connect(self.db_path_or_url)
        else:
            return sqlite3.connect(self.db_path_or_url)
    
    def execute(self, query, params=None):
        # Адаптация SQL запросов для PostgreSQL
        # Замена ? на %s, и т.д.
        pass
```

#### 3.2 Постепенная замена sqlite3.connect
- Создать функции-обертки
- Заменить по одному файлу
- Тестировать после каждого изменения

---

### Фаза 4: Миграция схемы БД в PostgreSQL

#### 4.1 Создание скрипта миграции
```python
# scripts/migrate_sqlite_to_postgres.py
"""
Скрипт для миграции данных из SQLite в PostgreSQL
- Читает все таблицы из SQLite
- Создает соответствующие таблицы в PostgreSQL
- Копирует данные
- Валидирует целостность
"""
```

#### 4.2 Структура PostgreSQL
- Одна база данных `domos`
- Разные схемы для разных сервисов:
  - `main` - основная БД (users, payments, etc.)
  - `advert` - токены рекламы
  - `contract` - токены контрактов
  - `django` - Django таблицы
  - `bot` - дополнительные таблицы бота

---

### Фаза 5: Обновление кода для поддержки обеих БД

#### 5.1 Создание конфигурации
```python
# config.py (обновленный)
import os

DB_TYPE = os.getenv("DB_TYPE", "sqlite")

if DB_TYPE == "postgres":
    DATABASE_URL = os.getenv("DATABASE_URL")
    MAIN_DB_PATH = DATABASE_URL  # или отдельный URL для каждой БД
    ADVERT_TOKENS_DB_PATH = DATABASE_URL
    CONTRACT_TOKENS_DB_PATH = DATABASE_URL
else:
    # Текущие пути к SQLite
    MAIN_DB_PATH = os.path.join(BASE_DIR, "bot", "tgbot", "databases", "data.db")
    ADVERT_TOKENS_DB_PATH = os.path.join(BASE_DIR, "api", "advert_tokens.db")
    CONTRACT_TOKENS_DB_PATH = os.path.join(BASE_DIR, "api", "contract_tokens.db")
```

#### 5.2 Обновление Django settings
```python
# web/web/settings.py
if os.getenv("DB_TYPE") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "domos"),
            "USER": os.getenv("POSTGRES_USER", "domos"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
            "HOST": os.getenv("POSTGRES_HOST", "postgres"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    # Текущая SQLite конфигурация
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
```

---

### Фаза 6: Тестирование в Docker (параллельно с production)

#### 6.1 Локальное тестирование
- Запуск Docker Compose локально
- Миграция тестовых данных
- Проверка всех функций

#### 6.2 Staging окружение
- Развертывание на отдельном сервере/портах
- Полная миграция данных
- Тестирование под нагрузкой

---

### Фаза 7: Постепенный переход

#### 7.1 Вариант A: Blue-Green Deployment
1. Запустить новую версию на других портах (8003, 8004, etc.)
2. Переключить nginx на новые порты
3. Мониторить работу
4. При проблемах - откат на старые порты

#### 7.2 Вариант B: Постепенная миграция сервисов
1. Сначала мигрировать API (менее критичный)
2. Потом Web
3. В последнюю очередь Bot (самый критичный)

---

## Детальный план выполнения

### Этап 1: Подготовка (1-2 дня)
- [ ] Создать ветку `feature/docker-postgres-migration`
- [ ] Собрать все requirements.txt в один
- [ ] Создать полный бэкап всех SQLite баз
- [ ] Документировать текущие настройки
- [ ] Создать структуру папок для Docker

### Этап 2: Docker инфраструктура (2-3 дня)
- [ ] Создать docker-compose.yml
- [ ] Создать Dockerfile для каждого сервиса
- [ ] Настроить PostgreSQL контейнер
- [ ] Настроить volumes для данных
- [ ] Настроить networking между сервисами
- [ ] Создать .env.docker с переменными

### Этап 3: Абстракция БД (3-4 дня)
- [ ] Создать модуль database.py с абстракцией
- [ ] Создать функции-обертки для sqlite3/psycopg2
- [ ] Обновить config.py для поддержки обеих БД
- [ ] Создать утилиты для миграции SQL запросов (? -> %s)

### Этап 4: Миграция схемы (2-3 дня)
- [ ] Создать скрипт анализа SQLite схем
- [ ] Создать скрипт генерации PostgreSQL схем
- [ ] Создать скрипт миграции данных
- [ ] Протестировать миграцию на копии данных

### Этап 5: Обновление кода (5-7 дней)
- [ ] Обновить все sqlite3.connect на новую абстракцию
- [ ] Обновить все aiosqlite.connect
- [ ] Адаптировать SQL запросы для PostgreSQL
- [ ] Обновить Django settings
- [ ] Обновить все импорты и зависимости

### Этап 6: Тестирование (3-5 дней)
- [ ] Локальное тестирование в Docker
- [ ] Миграция тестовых данных
- [ ] Проверка всех функций
- [ ] Нагрузочное тестирование
- [ ] Исправление найденных проблем

### Этап 7: Развертывание (2-3 дня)
- [ ] Развертывание на staging
- [ ] Миграция production данных
- [ ] Переключение nginx
- [ ] Мониторинг работы
- [ ] Откат при необходимости

---

## Риски и меры предосторожности

### Риски:
1. **Потеря данных** - митигируется полным бэкапом
2. **Простой сервиса** - митигируется blue-green deployment
3. **Несовместимость SQL** - митигируется тестированием
4. **Проблемы с производительностью** - митигируется нагрузочным тестированием

### Меры предосторожности:
1. Всегда держать текущую версию работающей
2. Полный бэкап перед любыми изменениями
3. Постепенная миграция по одному сервису
4. Возможность быстрого отката
5. Мониторинг логов и метрик

---

## Откат

### Процедура отката:
1. Остановить Docker контейнеры
2. Переключить nginx на старые порты (8001, 8002)
3. Запустить старые сервисы через screen
4. Восстановить SQLite базы из бэкапа (если нужно)
5. Проверить работу всех сервисов

### Хранение бэкапов:
- SQLite базы: `/backup/sqlite/YYYY-MM-DD/`
- PostgreSQL дампы: `/backup/postgres/YYYY-MM-DD/`
- Конфигурации: `/backup/config/YYYY-MM-DD/`

---

## Дополнительные улучшения

После успешной миграции можно добавить:
1. Redis для кеширования
2. Nginx внутри Docker для балансировки
3. Мониторинг (Prometheus + Grafana)
4. Логирование (ELK stack)
5. Автоматические бэкапы PostgreSQL

---

## Оценка времени

- **Минимальная оценка**: 15-20 рабочих дней
- **Реалистичная оценка**: 20-25 рабочих дней
- **С учетом непредвиденных проблем**: 25-30 рабочих дней

---

## Важные замечания

### Сохранение текущей рабочей версии
- Все изменения будут в отдельной ветке `feature/docker-postgres-migration`
- Текущая ветка `main` останется нетронутой
- Можно в любой момент переключиться обратно на `main`
- SQLite базы останутся на месте и будут работать параллельно

### Переменная окружения для переключения
Добавить переменную `DB_TYPE=sqlite|postgres` для переключения между БД без изменения кода.

### Мониторинги в Docker
Мониторинги можно запустить как:
1. Отдельные контейнеры (рекомендуется)
2. Фоновые задачи внутри bot контейнера
3. Отдельный сервис `monitors` в docker-compose

---

## Следующие шаги

1. ✅ Согласовать план (этот документ)
2. Создать ветку для миграции: `git checkout -b feature/docker-postgres-migration`
3. Начать с Этапа 1 (Подготовка)
4. Постепенно выполнять этапы с тестированием на каждом шаге
