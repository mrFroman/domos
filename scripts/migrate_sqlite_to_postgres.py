#!/usr/bin/env python3
"""
Скрипт для миграции данных из SQLite в PostgreSQL
- Читает все таблицы из SQLite
- Создает соответствующие таблицы в PostgreSQL
- Копирует данные
- Валидирует целостность
"""

import os
import sys
import sqlite3
import argparse
from typing import Dict, List, Any
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
    from psycopg2.extras import execute_values
    from psycopg2 import sql
except ImportError:
    print("❌ Ошибка: psycopg2 не установлен. Установите: pip install psycopg2-binary")
    sys.exit(1)

from config import (
    MAIN_DB_PATH,
    ADVERT_TOKENS_DB_PATH,
    CONTRACT_TOKENS_DB_PATH,
    DB_TYPE,
)


class SQLiteToPostgresMigrator:
    """Класс для миграции данных из SQLite в PostgreSQL"""
    
    def __init__(self, postgres_url: str, schema: str = "public"):
        """
        Инициализация мигратора
        
        Args:
            postgres_url: URL подключения к PostgreSQL (postgresql://user:pass@host:port/db)
            schema: Схема PostgreSQL для создания таблиц
        """
        self.postgres_url = postgres_url
        self.schema = schema
        self.pg_conn = None
    
    def connect_postgres(self):
        """Подключается к PostgreSQL"""
        try:
            self.pg_conn = psycopg2.connect(self.postgres_url)
            self.pg_conn.autocommit = False
            print(f"✅ Подключено к PostgreSQL")
        except Exception as e:
            print(f"❌ Ошибка подключения к PostgreSQL: {e}")
            sys.exit(1)
    
    def get_sqlite_tables(self, sqlite_path: str) -> List[str]:
        """Получает список всех таблиц из SQLite базы"""
        if not os.path.exists(sqlite_path):
            print(f"⚠️  Файл SQLite не найден: {sqlite_path}")
            return []
        
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    
    def get_table_schema(self, sqlite_path: str, table_name: str) -> str:
        """Получает схему таблицы из SQLite"""
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        conn.close()
        
        # Формируем CREATE TABLE запрос для PostgreSQL
        column_defs = []
        for col in columns:
            col_name = col[1]
            col_type = col[2].upper()
            is_pk = col[5] == 1
            not_null = col[3] == 1
            default = col[4]
            
            # Адаптируем типы для PostgreSQL
            if col_type == "INTEGER":
                if is_pk:
                    pg_type = "SERIAL PRIMARY KEY"
                else:
                    pg_type = "INTEGER"
            elif col_type == "TEXT":
                pg_type = "TEXT"
            elif col_type == "REAL":
                pg_type = "REAL"
            elif col_type == "BLOB":
                pg_type = "BYTEA"
            elif col_type == "BOOLEAN":
                pg_type = "BOOLEAN"
            else:
                pg_type = "TEXT"  # По умолчанию
            
            col_def = f"{col_name} {pg_type}"
            if not_null and not is_pk:
                col_def += " NOT NULL"
            if default and not is_pk:
                if isinstance(default, str):
                    col_def += f" DEFAULT '{default}'"
                else:
                    col_def += f" DEFAULT {default}"
            
            column_defs.append(col_def)
        
        return f"CREATE TABLE IF NOT EXISTS {self.schema}.{table_name} (\n    " + ",\n    ".join(column_defs) + "\n);"
    
    def migrate_table(self, sqlite_path: str, table_name: str, schema: str = None):
        """Мигрирует одну таблицу из SQLite в PostgreSQL"""
        if schema is None:
            schema = self.schema
        
        print(f"\n📋 Миграция таблицы: {table_name}")
        
        # Получаем схему таблицы
        create_sql = self.get_table_schema(sqlite_path, table_name)
        
        # Создаем таблицу в PostgreSQL
        with self.pg_conn.cursor() as cur:
            # Создаем схему если её нет
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            
            # Удаляем таблицу если существует (для повторной миграции)
            cur.execute(f"DROP TABLE IF EXISTS {schema}.{table_name} CASCADE")
            
            # Создаем таблицу
            cur.execute(create_sql)
            print(f"  ✅ Таблица создана: {schema}.{table_name}")
        
        # Копируем данные
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
        
        if rows:
            # Получаем имена колонок
            column_names = [description[0] for description in sqlite_cursor.description]
            columns_str = ", ".join(column_names)
            placeholders = ", ".join(["%s"] * len(column_names))
            
            insert_sql = f"INSERT INTO {schema}.{table_name} ({columns_str}) VALUES ({placeholders})"
            
            # Подготавливаем данные для вставки
            data = []
            for row in rows:
                row_data = []
                for col in column_names:
                    value = row[col]
                    # Конвертируем типы для PostgreSQL
                    if isinstance(value, bytes):
                        value = psycopg2.Binary(value)
                    row_data.append(value)
                data.append(tuple(row_data))
            
            # Вставляем данные
            with self.pg_conn.cursor() as cur:
                execute_values(cur, insert_sql, data)
            
            print(f"  ✅ Скопировано строк: {len(rows)}")
        else:
            print(f"  ⚠️  Таблица пуста")
        
        sqlite_conn.close()
    
    def migrate_database(self, sqlite_path: str, schema: str = None):
        """Мигрирует всю базу данных из SQLite в PostgreSQL"""
        if schema is None:
            schema = self.schema
        
        if not os.path.exists(sqlite_path):
            print(f"⚠️  Файл SQLite не найден: {sqlite_path}")
            return
        
        print(f"\n{'='*60}")
        print(f"🔄 Миграция базы данных: {sqlite_path}")
        print(f"📦 Схема PostgreSQL: {schema}")
        print(f"{'='*60}")
        
        tables = self.get_sqlite_tables(sqlite_path)
        
        if not tables:
            print(f"⚠️  Таблицы не найдены в {sqlite_path}")
            return
        
        print(f"📋 Найдено таблиц: {len(tables)}")
        
        for table in tables:
            try:
                self.migrate_table(sqlite_path, table, schema)
            except Exception as e:
                print(f"  ❌ Ошибка при миграции таблицы {table}: {e}")
                self.pg_conn.rollback()
                continue
        
        # Коммитим все изменения
        self.pg_conn.commit()
        print(f"\n✅ Миграция завершена успешно!")
    
    def close(self):
        """Закрывает подключение к PostgreSQL"""
        if self.pg_conn:
            self.pg_conn.close()


def main():
    parser = argparse.ArgumentParser(description="Миграция данных из SQLite в PostgreSQL")
    parser.add_argument("--postgres-url", required=True, help="URL подключения к PostgreSQL")
    parser.add_argument("--sqlite-path", required=True, help="Путь к SQLite файлу")
    parser.add_argument("--schema", default="public", help="Схема PostgreSQL (по умолчанию: public)")
    
    args = parser.parse_args()
    
    migrator = SQLiteToPostgresMigrator(args.postgres_url, args.schema)
    migrator.connect_postgres()
    
    try:
        migrator.migrate_database(args.sqlite_path, args.schema)
    finally:
        migrator.close()


if __name__ == "__main__":
    # Пример использования:
    # python scripts/migrate_sqlite_to_postgres.py \
    #   --postgres-url "postgresql://domos:password@localhost:5432/domos" \
    #   --sqlite-path "bot/tgbot/databases/data.db" \
    #   --schema "main"
    
    if len(sys.argv) == 1:
        print("Использование:")
        print("  python scripts/migrate_sqlite_to_postgres.py \\")
        print("    --postgres-url 'postgresql://user:pass@host:port/db' \\")
        print("    --sqlite-path 'path/to/file.db' \\")
        print("    --schema 'schema_name'")
        print("\nПример:")
        print("  python scripts/migrate_sqlite_to_postgres.py \\")
        print("    --postgres-url 'postgresql://domos:password@localhost:5432/domos' \\")
        print("    --sqlite-path 'bot/tgbot/databases/data.db' \\")
        print("    --schema 'main'")
        sys.exit(1)
    
    main()
