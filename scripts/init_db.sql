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

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS main.users (
    user_id BIGINT PRIMARY KEY,
    pay_status INTEGER DEFAULT 0,
    last_pay BIGINT DEFAULT 0,
    rank INTEGER DEFAULT 0,
    end_pay BIGINT DEFAULT 0,
    fullName VARCHAR(255),
    banned INTEGER DEFAULT 0,
    full_name VARCHAR(255),
    ref_id BIGINT DEFAULT 0
);

-- Таблица платежей
CREATE TABLE IF NOT EXISTS main.payments (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    payment_id VARCHAR(255),
    amount DECIMAL(10, 2),
    ts BIGINT,
    status INTEGER DEFAULT 0,
    ref VARCHAR(255) DEFAULT '404'
);

-- Таблица рекуррентных платежей
CREATE TABLE IF NOT EXISTS main.rec_payments (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    amount DECIMAL(10, 2),
    currency VARCHAR(10) DEFAULT 'RUB',
    is_recurrent INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'pending',
    rebill_id VARCHAR(255),
    payment_id_last VARCHAR(255),
    start_pay_date TIMESTAMP,
    end_pay_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица админ-ссылок
CREATE TABLE IF NOT EXISTS main.admin (
    id SERIAL PRIMARY KEY,
    link_id VARCHAR(255),
    activated INTEGER DEFAULT 0
);

-- Таблица запросов
CREATE TABLE IF NOT EXISTS main.requests (
    id SERIAL PRIMARY KEY,
    request_type VARCHAR(100),
    request_date TIMESTAMP,
    request_text TEXT,
    user_full_name VARCHAR(255),
    user_username VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица обратной связи
CREATE TABLE IF NOT EXISTS main.feedback (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_users_pay_status ON main.users(pay_status);
CREATE INDEX IF NOT EXISTS idx_users_end_pay ON main.users(end_pay);
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON main.payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON main.payments(status);
