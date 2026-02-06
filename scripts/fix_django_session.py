#!/usr/bin/env python3
"""
Скрипт для исправления типа поля expire_date в таблице django_session.
Исправляет ошибку: operator does not exist: text > timestamp with time zone
"""

import os
import sys
import psycopg2
from psycopg2 import sql

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fix_django_session():
    """Исправляет тип поля expire_date в таблице django_session"""
    
    # Получаем параметры подключения из переменных окружения
    db_name = os.getenv("POSTGRES_DB", "domos")
    db_user = os.getenv("POSTGRES_USER", "domos")
    db_password = os.getenv("POSTGRES_PASSWORD", "")
    db_host = os.getenv("POSTGRES_HOST", "postgres")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    
    try:
        # Подключаемся к БД
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            options="-c search_path=django,public"
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Проверяем существование таблицы
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'django' 
                AND table_name = 'django_session'
            )
        """)
        
        if not cursor.fetchone()[0]:
            print("❌ Таблица django_session не существует в схеме django")
            print("💡 Возможно, нужно сначала выполнить миграции Django:")
            print("   docker-compose exec web python manage.py migrate")
            return False
        
        # Проверяем тип поля expire_date
        cursor.execute("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'django' 
            AND table_name = 'django_session' 
            AND column_name = 'expire_date'
        """)
        
        result = cursor.fetchone()
        if not result:
            print("❌ Поле expire_date не найдено в таблице django_session")
            return False
        
        current_type = result[0]
        print(f"📋 Текущий тип поля expire_date: {current_type}")
        
        if current_type == 'text':
            print("🔧 Исправляю тип поля expire_date...")
            
            # Очищаем некорректные значения (если есть)
            cursor.execute("""
                UPDATE django.django_session 
                SET expire_date = NULL 
                WHERE expire_date !~ '^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}'
            """)
            cleaned = cursor.rowcount
            if cleaned > 0:
                print(f"   Очищено {cleaned} некорректных значений")
            
            # Изменяем тип поля
            cursor.execute("""
                ALTER TABLE django.django_session 
                ALTER COLUMN expire_date TYPE timestamp with time zone 
                USING expire_date::timestamp with time zone
            """)
            
            print("✅ Тип поля expire_date успешно изменен на timestamp with time zone")
            return True
        elif current_type in ('timestamp with time zone', 'timestamptz'):
            print("✅ Поле expire_date уже имеет правильный тип")
            return True
        else:
            print(f"⚠️  Неожиданный тип поля: {current_type}")
            print("   Попытка конвертации...")
            
            try:
                cursor.execute("""
                    ALTER TABLE django.django_session 
                    ALTER COLUMN expire_date TYPE timestamp with time zone 
                    USING expire_date::timestamp with time zone
                """)
                print("✅ Тип поля успешно изменен")
                return True
            except Exception as e:
                print(f"❌ Ошибка при конвертации: {e}")
                return False
        
    except psycopg2.Error as e:
        print(f"❌ Ошибка PostgreSQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🔧 Исправление типа поля expire_date в таблице django_session...")
    print()
    
    success = fix_django_session()
    
    print()
    if success:
        print("✅ Проблема исправлена! Теперь можно перезапустить веб-сервер.")
    else:
        print("❌ Не удалось исправить проблему. Проверьте логи выше.")
        sys.exit(1)

