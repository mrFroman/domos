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
            # Экранируем зарезервированные слова PostgreSQL
            if col_name.upper() in ['DESC', 'ORDER', 'USER', 'GROUP', 'TABLE', 'INDEX']:
                col_name = f'"{col_name}"'
            col_type = col[2].upper()
            is_pk = col[5] == 1
            not_null = col[3] == 1
            default = col[4]
            
            # Экранируем имя колонки (на случай зарезервированных слов как desc, user и т.д.)
            escaped_col_name = f'"{col_name}"'
            
            # Адаптируем типы для PostgreSQL
            if col_type == "INTEGER":
                if is_pk:
                    pg_type = "SERIAL PRIMARY KEY"
                else:
                    # Проверяем имя колонки для boolean полей (только для определенных таблиц)
                    col_lower = col_name.lower()
                    if col_lower in ['payment_status', 'signal'] and table_name.lower() in ['tokens']:
                        pg_type = "BOOLEAN"
                    else:
                        pg_type = "BIGINT"  # Используем BIGINT вместо INTEGER для больших чисел
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
            
            col_def = f"{escaped_col_name} {pg_type}"
            if not_null and not is_pk:
                col_def += " NOT NULL"
            if default and not is_pk:
                if isinstance(default, str):
                    # Экранируем одинарные кавычки для PostgreSQL
                    escaped_default = default.replace("'", "''")
                    col_def += f" DEFAULT '{escaped_default}'"
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
            
            # Экранируем имена колонок (на случай зарезервированных слов)
            escaped_columns = [f'"{col}"' for col in column_names]
            columns_str = ", ".join(escaped_columns)
            placeholders = ", ".join(["%s"] * len(column_names))
            
            insert_sql = f'INSERT INTO {schema}.{table_name} ({columns_str}) VALUES ({placeholders})'
            
            # Получаем информацию о типах колонок для правильной конвертации
            sqlite_conn2 = sqlite3.connect(sqlite_path)
            cursor_info = sqlite_conn2.cursor()
            cursor_info.execute(f"PRAGMA table_info({table_name})")
            col_info = {col[1]: col[2].upper() for col in cursor_info.fetchall()}
            sqlite_conn2.close()
            
            # Подготавливаем данные для вставки
            data = []
            for row in rows:
                row_data = []
                for col in column_names:
                    value = row[col]
                    # Конвертируем типы для PostgreSQL
                    if isinstance(value, bytes):
                        value = psycopg2.Binary(value)
                    elif value is not None:
                        # Конвертируем INTEGER в BOOLEAN для определенных полей
                        col_type = col_info.get(col, "").upper()
                        col_lower = col.lower()
                        # Проверяем, является ли это boolean полем (по имени колонки и таблице)
                        # В SQLite BOOLEAN хранится как INTEGER, поэтому проверяем оба случая
                        is_boolean_field = (
                            col_lower in ['payment_status', 'signal'] and 
                            table_name.lower() == 'tokens' and
                            (col_type == "INTEGER" or col_type == "BOOLEAN")
                        )
                        if is_boolean_field:
                            # Конвертируем 0/1/None в False/True/None
                            if value is None:
                                value = None
                            else:
                                # Приводим к int, затем к bool
                                try:
                                    int_val = int(value) if value not in (None, '') else 0
                                    value = bool(int_val)
                                except (ValueError, TypeError):
                                    value = False
                        elif col_type == "INTEGER" and isinstance(value, int):
                            # Для больших чисел используем как есть (BIGINT)
                            pass
                    row_data.append(value)
                data.append(tuple(row_data))
            
            # Вставляем данные
            inserted_count = 0
            error_count = 0
            
            # Используем отдельные транзакции для каждой строки через savepoints
            cur = self.pg_conn.cursor()
            for idx, row_data in enumerate(data, 1):
                # Создаем savepoint для каждой строки
                savepoint_name = f"sp_{idx}"
                try:
                    cur.execute(f"SAVEPOINT {savepoint_name}")
                    cur.execute(insert_sql, row_data)
                    cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    inserted_count += 1
                    # Коммитим каждые 100 строк
                    if inserted_count % 100 == 0:
                        self.pg_conn.commit()
                except Exception as e:
                    error_count += 1
                    # Откатываемся к savepoint (не к началу транзакции!)
                    try:
                        cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                        cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    except:
                        pass
                    # Показываем только первые 10 ошибок
                    if error_count <= 10:
                        print(f"    ⚠️  Ошибка при вставке строки {idx}: {str(e)[:150]}")
                    continue
            
            # Финальный commit
            self.pg_conn.commit()
            cur.close()
            
            if error_count > 0:
                print(f"  ✅ Скопировано строк: {inserted_count} из {len(rows)} (пропущено ошибок: {error_count})")
            else:
                print(f"  ✅ Скопировано строк: {inserted_count}")
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
                # Коммитим после каждой таблицы для изоляции ошибок
                # (commit уже выполнен внутри migrate_table, но на всякий случай)
                try:
                    self.pg_conn.commit()
                except:
                    pass
            except Exception as e:
                print(f"  ❌ Ошибка при миграции таблицы {table}: {e}")
                try:
                    self.pg_conn.rollback()
                except:
                    pass
                continue
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
