-- Инициализация PostgreSQL базы данных
-- Этот скрипт выполняется автоматически при первом запуске контейнера PostgreSQL

-- Создаем схемы для разных сервисов
CREATE SCHEMA IF NOT EXISTS main;
CREATE SCHEMA IF NOT EXISTS advert;
CREATE SCHEMA IF NOT EXISTS contract;
CREATE SCHEMA IF NOT EXISTS django;
CREATE SCHEMA IF NOT EXISTS bot;

-- Устанавливаем права доступа
GRANT ALL PRIVILEGES ON SCHEMA main TO domos;
GRANT ALL PRIVILEGES ON SCHEMA advert TO domos;
GRANT ALL PRIVILEGES ON SCHEMA contract TO domos;
GRANT ALL PRIVILEGES ON SCHEMA django TO domos;
GRANT ALL PRIVILEGES ON SCHEMA bot TO domos;

-- Комментарии к схемам
COMMENT ON SCHEMA main IS 'Основная БД (users, payments, etc.)';
COMMENT ON SCHEMA advert IS 'Токены рекламы';
COMMENT ON SCHEMA contract IS 'Токены контрактов';
COMMENT ON SCHEMA django IS 'Django таблицы';
COMMENT ON SCHEMA bot IS 'Дополнительные таблицы бота';
