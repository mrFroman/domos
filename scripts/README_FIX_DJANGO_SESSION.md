# Исправление ошибки django_session

## Проблема

Ошибка: `operator does not exist: text > timestamp with time zone`

Поле `expire_date` в таблице `django_session` имеет неправильный тип данных (`text` вместо `timestamp with time zone`).

## Решение

### Вариант 1: Использование Python-скрипта (рекомендуется)

```bash
# Убедитесь, что контейнеры запущены
docker-compose up -d postgres

# Выполните скрипт из контейнера web (где есть доступ к переменным окружения)
docker-compose exec web python /app/scripts/fix_django_session.py

# Или если скрипт находится на хосте
docker-compose exec web python scripts/fix_django_session.py
```

### Вариант 2: Использование SQL-скрипта

```bash
# Выполните SQL-скрипт напрямую в PostgreSQL
docker-compose exec postgres psql -U domos -d domos -f /docker-entrypoint-initdb.d/fix_django_session.sql

# Или если скрипт находится на хосте
docker-compose exec -T postgres psql -U domos -d domos < scripts/fix_django_session.sql
```

### Вариант 3: Пересоздание таблицы через миграции Django

Если скрипты не помогли, можно пересоздать таблицу:

```bash
# Удалить таблицу (ОСТОРОЖНО: это удалит все сессии!)
docker-compose exec postgres psql -U domos -d domos -c "DROP TABLE IF EXISTS django.django_session;"

# Пересоздать таблицу через миграции Django
docker-compose exec web python manage.py migrate sessions
```

## Проверка

После исправления проверьте, что тип поля правильный:

```bash
docker-compose exec postgres psql -U domos -d domos -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'django' AND table_name = 'django_session' AND column_name = 'expire_date';"
```

Ожидаемый результат:
```
 column_name  |        data_type        
--------------+-------------------------
 expire_date  | timestamp with time zone
```

## Причина проблемы

Эта проблема может возникнуть, если:
1. Таблица была создана вручную с неправильным типом
2. Миграции Django не были применены правильно
3. Произошла миграция данных из SQLite, где типы данных обрабатываются по-другому

