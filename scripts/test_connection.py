#!/usr/bin/env python3
"""
Скрипт для проверки подключения к PostgreSQL
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("❌ psycopg2 не установлен. Установите: pip install psycopg2-binary")
    sys.exit(1)

# Параметры подключения
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "domos")
POSTGRES_USER = os.getenv("POSTGRES_USER", "domos")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

if not POSTGRES_PASSWORD:
    print("❌ POSTGRES_PASSWORD не установлен в переменных окружения")
    sys.exit(1)

def test_connection():
    """Тестирует подключение к PostgreSQL"""
    try:
        print(f"🔌 Подключение к PostgreSQL...")
        print(f"   Host: {POSTGRES_HOST}")
        print(f"   Port: {POSTGRES_PORT}")
        print(f"   Database: {POSTGRES_DB}")
        print(f"   User: {POSTGRES_USER}")
        
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        
        print("✅ Подключение успешно!")
        
        # Проверяем схемы
        cursor = conn.cursor()
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name IN ('main', 'advert', 'contract', 'django', 'bot')
            ORDER BY schema_name
        """)
        
        schemas = cursor.fetchall()
        print(f"\n📋 Найденные схемы:")
        for schema in schemas:
            print(f"   - {schema[0]}")
        
        # Проверяем таблицы в каждой схеме
        for schema in schemas:
            schema_name = schema[0]
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s
                ORDER BY table_name
            """, (schema_name,))
            
            tables = cursor.fetchall()
            if tables:
                print(f"\n   Таблицы в схеме '{schema_name}':")
                for table in tables:
                    print(f"     - {table[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Все проверки пройдены успешно!")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Ошибка подключения: {e}")
        print("\n💡 Проверьте:")
        print("   1. PostgreSQL контейнер запущен: docker-compose ps")
        print("   2. Переменные окружения установлены правильно")
        print("   3. Пароль указан верно")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
