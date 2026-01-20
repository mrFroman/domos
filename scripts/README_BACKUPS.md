# Автоматические бэкапы PostgreSQL

## Описание

Система автоматических бэкапов PostgreSQL настроена для ежедневного создания бэкапов базы данных с автоматическим удалением старых бэкапов (старше 7 дней).

## Как это работает

1. **Автоматический бэкап**: Каждый день в 3:00 по московскому времени создается бэкап базы данных
2. **Хранение**: Бэкапы хранятся в директории `./scripts/backups/`
3. **Ротация**: Автоматически удаляются бэкапы старше 7 дней
4. **Формат**: Бэкапы сохраняются в формате `domos_YYYY-MM-DD_HH-MM-SS.sql.gz`

## Файлы

- `backup_postgres.sh` - Bash скрипт для создания бэкапа (используется в cron)
- `backup_postgres.py` - Python версия скрипта (альтернатива)
- `restore_postgres.sh` - Скрипт для восстановления из бэкапа

## Использование

### Автоматический бэкап

Бэкапы создаются автоматически через Docker сервис `postgres_backup`. Никаких дополнительных действий не требуется.

### Ручной запуск бэкапа

```bash
# Через Docker
docker exec domos_postgres_backup /backup_postgres.sh

# Или напрямую (если скрипт на хосте)
./scripts/backup_postgres.sh
```

### Просмотр бэкапов

```bash
# Список всех бэкапов
ls -lh scripts/backups/

# Последние бэкапы
ls -lht scripts/backups/ | head -10
```

### Восстановление из бэкапа

```bash
# Показать доступные бэкапы
./scripts/restore_postgres.sh

# Восстановить из конкретного бэкапа
./scripts/restore_postgres.sh scripts/backups/domos_2025-01-19_03-00-00.sql.gz
```

## Настройка

### Изменение времени бэкапа

Отредактируйте `docker-compose.yml`, изменив cron расписание:
```yaml
echo '0 3 * * * /backup_postgres.sh ...'  # 3:00 каждый день
echo '0 2 * * * /backup_postgres.sh ...'  # 2:00 каждый день
```

### Изменение периода хранения

Измените переменную `RETENTION_DAYS` в `docker-compose.yml`:
```yaml
RETENTION_DAYS: 7  # Хранить 7 дней
RETENTION_DAYS: 14 # Хранить 14 дней
```

### Изменение директории бэкапов

Измените `BACKUP_DIR` в `docker-compose.yml` и volume mapping:
```yaml
volumes:
  - /path/to/backups:/backups/postgres
```

## Мониторинг

Логи бэкапов сохраняются в `scripts/backups/backup.log`:
```bash
# Просмотр последних логов
tail -f scripts/backups/backup.log

# Проверка последнего бэкапа
ls -lht scripts/backups/ | head -1
```

## Безопасность

⚠️ **Важно**: 
- Бэкапы содержат все данные базы, включая пароли и токены
- Убедитесь, что директория `scripts/backups/` защищена от несанкционированного доступа
- Рекомендуется настроить дополнительное копирование бэкапов на внешний сервер

## Устранение неполадок

### Бэкапы не создаются

1. Проверьте логи: `docker logs domos_postgres_backup`
2. Проверьте права доступа к директории: `ls -ld scripts/backups/`
3. Проверьте переменные окружения: `docker exec domos_postgres_backup env | grep POSTGRES`

### Недостаточно места на диске

1. Проверьте размер бэкапов: `du -sh scripts/backups/`
2. Уменьшите период хранения (RETENTION_DAYS)
3. Очистите старые бэкапы вручную: `find scripts/backups/ -name "*.sql.gz" -mtime +7 -delete`
