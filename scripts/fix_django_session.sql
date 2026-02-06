-- Исправление типа поля expire_date в таблице django_session
-- Проблема: поле expire_date имеет тип text вместо timestamp with time zone
-- Это вызывает ошибку: operator does not exist: text > timestamp with time zone

-- Проверяем текущий тип поля
DO $$
BEGIN
    -- Проверяем, существует ли таблица
    IF EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'django' 
        AND table_name = 'django_session'
    ) THEN
        -- Проверяем тип поля expire_date
        IF EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'django' 
            AND table_name = 'django_session' 
            AND column_name = 'expire_date'
            AND data_type = 'text'
        ) THEN
            -- Конвертируем text в timestamp with time zone
            -- Сначала очищаем некорректные значения (если есть)
            UPDATE django.django_session 
            SET expire_date = NULL 
            WHERE expire_date !~ '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}';
            
            -- Изменяем тип поля
            ALTER TABLE django.django_session 
            ALTER COLUMN expire_date TYPE timestamp with time zone 
            USING expire_date::timestamp with time zone;
            
            RAISE NOTICE 'Тип поля expire_date успешно изменен на timestamp with time zone';
        ELSE
            RAISE NOTICE 'Поле expire_date уже имеет правильный тип или не существует';
        END IF;
    ELSE
        RAISE NOTICE 'Таблица django_session не существует в схеме django';
    END IF;
END $$;

