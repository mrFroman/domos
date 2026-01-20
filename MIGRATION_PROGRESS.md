# Прогресс миграции на PostgreSQL

## ✅ Выполнено

### Инфраструктура
- [x] Docker Compose конфигурация
- [x] Dockerfile для всех сервисов
- [x] Автоматические бэкапы PostgreSQL
- [x] Скрипты миграции данных

### Абстракция БД
- [x] Модуль `database.py` с поддержкой SQLite и PostgreSQL
- [x] Синхронные и асинхронные операции
- [x] Автоматическая адаптация SQL запросов

### Обновление кода
- [x] `config.py` - поддержка обеих БД
- [x] `web/web/settings.py` - поддержка PostgreSQL
- [x] `api/main.py` - частично обновлен:
  - [x] `init_db()` - использует абстракцию
  - [x] `save_passport_data1()` - использует абстракцию
  - [x] `load_data()` - использует async абстракцию
  - [x] `load_advert_data()` - использует async абстракцию
  - [x] `save_advert_data_api()` - использует абстракцию
  - [ ] Остальные функции в `api/main.py` (webhook handlers, etc.)

## 🔄 В процессе

### Файлы, требующие обновления

1. **api/main.py** - осталось обновить:
   - `wait_advert_payment_signal()` - устаревшая функция (polling)
   - `create_advert_payment()` - webhook handler
   - `yookassa_webhook()` - webhook handler
   - `mark_payment_failed()` - функция для Tinkoff
   - `tinkoff_recurrent_payment_webhook()` - webhook handler

2. **bot/tgbot/databases/pay_db.py** - основной файл работы с БД бота
   - Много функций используют `sqlite3.connect`
   - Нужна полная замена на абстракцию

3. **bot/tgbot/handlers/advert_new.py** - обработка рекламы
   - `_token_exists()` - использует `sqlite3.connect`

4. **Другие файлы** (25+ файлов):
   - Различные handlers и services
   - Мониторинги
   - Парсеры

## 📝 Стратегия замены

### Шаблон замены для синхронных операций:

**Было:**
```python
with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.execute("SELECT * FROM table WHERE id = ?", (id,))
    row = cursor.fetchone()
```

**Стало:**
```python
from bot.tgbot.databases.database import DatabaseConnection

db = DatabaseConnection(DB_PATH, schema="main")
row = db.fetchone("SELECT * FROM table WHERE id = %s", (id,))
```

### Шаблон замены для async операций:

**Было:**
```python
async with aiosqlite.connect(DB_PATH) as conn:
    async with conn.execute("SELECT * FROM table WHERE id = ?", (id,)) as cursor:
        row = await cursor.fetchone()
```

**Стало:**
```python
from bot.tgbot.databases.database import async_fetch_one

row = await async_fetch_one(DB_PATH, "SELECT * FROM table WHERE id = %s", (id,), schema="main")
```

## ⚠️ Важные замечания

1. **Параметры запросов**: `?` заменяется на `%s` автоматически в `_adapt_sql_for_postgres()`
2. **Схемы**: Для PostgreSQL нужно указывать схему:
   - `main` - основная БД
   - `advert` - реклама
   - `contract` - контракты
   - `django` - Django таблицы
   - `bot` - дополнительные таблицы бота
3. **REPLACE INTO**: В PostgreSQL используется `INSERT ... ON CONFLICT DO UPDATE`
4. **Типы данных**: Автоматически адаптируются, но могут потребоваться ручные правки

## 🎯 Следующие шаги

1. Продолжить обновление `api/main.py`
2. Обновить `bot/tgbot/databases/pay_db.py`
3. Обновить handlers по приоритету использования
4. Протестировать на копии данных
5. Выполнить миграцию production данных
