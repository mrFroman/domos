"""
Абстракция для работы с SQLite и PostgreSQL
Позволяет переключаться между БД без изменения кода приложения
Поддерживает как синхронные, так и асинхронные операции
"""

import os
import sqlite3
from typing import Union, Optional, Any, List, Tuple
from contextlib import contextmanager, asynccontextmanager
import logging

logger = logging.getLogger(__name__)

# Определяем тип БД из переменной окружения
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # sqlite или postgres

# Импортируем PostgreSQL только если нужно
if DB_TYPE == "postgres":
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor, execute_values
        from psycopg2.pool import SimpleConnectionPool
        try:
            import asyncpg  # Для async PostgreSQL
            ASYNCPG_AVAILABLE = True
        except ImportError:
            ASYNCPG_AVAILABLE = False
        PSYCOPG2_AVAILABLE = True
    except ImportError:
        logger.warning("psycopg2 не установлен, PostgreSQL недоступен")
        PSYCOPG2_AVAILABLE = False
        ASYNCPG_AVAILABLE = False
else:
    PSYCOPG2_AVAILABLE = False
    ASYNCPG_AVAILABLE = False

# Импортируем aiosqlite для async SQLite
try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False
    logger.warning("aiosqlite не установлен, async SQLite недоступен")


class DatabaseConnection:
    """Абстракция для работы с SQLite и PostgreSQL"""
    
    def __init__(self, db_path_or_url: str, schema: Optional[str] = None):
        """
        Инициализация подключения к БД
        
        Args:
            db_path_or_url: Путь к SQLite файлу или URL для PostgreSQL
            schema: Схема PostgreSQL (для разделения данных разных сервисов)
        """
        self.db_path_or_url = db_path_or_url
        self.db_type = DB_TYPE
        self.schema = schema
        self._connection = None
        self._pool = None
        
        if self.db_type == "postgres" and not PSYCOPG2_AVAILABLE:
            raise RuntimeError("PostgreSQL выбран, но psycopg2 не установлен")
    
    def connect(self):
        """Создает подключение к БД"""
        if self.db_type == "postgres":
            if not self._pool:
                # Создаем пул подключений для PostgreSQL
                self._pool = SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=self.db_path_or_url
                )
            return self._pool.getconn()
        else:
            return sqlite3.connect(self.db_path_or_url)
    
    def close(self, conn):
        """Закрывает подключение"""
        if self.db_type == "postgres":
            if self._pool:
                self._pool.putconn(conn)
        else:
            conn.close()
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для получения подключения"""
        conn = self.connect()
        try:
            if self.db_type == "postgres" and self.schema:
                # Устанавливаем схему для PostgreSQL
                with conn.cursor() as cur:
                    cur.execute(f"SET search_path TO {self.schema}, public")
            yield conn
        finally:
            self.close(conn)
    
    def execute(self, query: str, params: Optional[Union[tuple, dict]] = None):
        """
        Выполняет SQL запрос
        
        Args:
            query: SQL запрос (адаптируется автоматически)
            params: Параметры запроса
        
        Returns:
            Результат выполнения запроса
        """
        # Адаптируем SQL для PostgreSQL
        if self.db_type == "postgres":
            query = self._adapt_sql_for_postgres(query)
        
        # Определяем, нужно ли возвращать результаты
        query_upper = query.strip().upper()
        is_select = query_upper.startswith("SELECT") or "RETURNING" in query_upper
        
        with self.get_connection() as conn:
            if self.db_type == "postgres":
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if params:
                        cur.execute(query, params)
                    else:
                        cur.execute(query)
                    conn.commit()
                    if is_select:
                        return cur.fetchall()
                    return []
            else:
                cur = conn.cursor()
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)
                conn.commit()
                if is_select:
                    return cur.fetchall()
                return []
    
    def execute_many(self, query: str, params_list: List[Union[tuple, dict]]):
        """
        Выполняет запрос с множественными параметрами
        
        Args:
            query: SQL запрос
            params_list: Список параметров
        """
        if self.db_type == "postgres":
            query = self._adapt_sql_for_postgres(query)
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    execute_values(cur, query, params_list)
                    conn.commit()
        else:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.executemany(query, params_list)
                conn.commit()
    
    def fetchone(self, query: str, params: Optional[Union[tuple, dict]] = None):
        """Выполняет запрос и возвращает одну строку"""
        if self.db_type == "postgres":
            query = self._adapt_sql_for_postgres(query)
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if params:
                        cur.execute(query, params)
                    else:
                        cur.execute(query)
                    return cur.fetchone()
        else:
            with self.get_connection() as conn:
                cur = conn.cursor()
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)
                return cur.fetchone()
    
    def fetchall(self, query: str, params: Optional[Union[tuple, dict]] = None):
        """Выполняет запрос и возвращает все строки"""
        if self.db_type == "postgres":
            query = self._adapt_sql_for_postgres(query)
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if params:
                        cur.execute(query, params)
                    else:
                        cur.execute(query)
                    return cur.fetchall()
        else:
            with self.get_connection() as conn:
                cur = conn.cursor()
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)
                return cur.fetchall()
    
    @staticmethod
    def _adapt_sql_for_postgres(query: str) -> str:
        """
        Адаптирует SQL запросы из SQLite формата в PostgreSQL
        
        - Заменяет ? на %s
        - Адаптирует типы данных
        - Исправляет синтаксические различия
        """
        # Заменяем ? на %s для параметров
        query = query.replace('?', '%s')
        
        # Заменяем INTEGER PRIMARY KEY на SERIAL PRIMARY KEY
        query = query.replace('INTEGER PRIMARY KEY', 'SERIAL PRIMARY KEY')
        
        # Заменяем AUTOINCREMENT на SERIAL
        query = query.replace('AUTOINCREMENT', '')
        
        # Заменяем TEXT на VARCHAR или TEXT (PostgreSQL поддерживает TEXT)
        # Оставляем как есть, PostgreSQL поддерживает TEXT
        
        # Заменяем BOOLEAN DEFAULT 0/1 на BOOLEAN DEFAULT FALSE/TRUE
        query = query.replace('BOOLEAN DEFAULT 0', 'BOOLEAN DEFAULT FALSE')
        query = query.replace('BOOLEAN DEFAULT 1', 'BOOLEAN DEFAULT TRUE')
        
        # Заменяем CURRENT_TIMESTAMP на NOW()
        query = query.replace('CURRENT_TIMESTAMP', 'NOW()')
        
        return query


# Функции-обертки для удобства использования
def get_db_connection(db_path_or_url: str, schema: Optional[str] = None) -> DatabaseConnection:
    """Создает и возвращает объект подключения к БД"""
    return DatabaseConnection(db_path_or_url, schema)


def execute_query(db_path_or_url: str, query: str, params: Optional[Union[tuple, dict]] = None, schema: Optional[str] = None):
    """Выполняет SQL запрос"""
    db = DatabaseConnection(db_path_or_url, schema)
    return db.execute(query, params)


def fetch_one(db_path_or_url: str, query: str, params: Optional[Union[tuple, dict]] = None, schema: Optional[str] = None):
    """Выполняет запрос и возвращает одну строку"""
    db = DatabaseConnection(db_path_or_url, schema)
    return db.fetchone(query, params)


def fetch_all(db_path_or_url: str, query: str, params: Optional[Union[tuple, dict]] = None, schema: Optional[str] = None):
    """Выполняет запрос и возвращает все строки"""
    db = DatabaseConnection(db_path_or_url, schema)
    return db.fetchall(query, params)


# ========== ASYNC ВЕРСИЯ ==========

class AsyncDatabaseConnection:
    """Асинхронная абстракция для работы с SQLite и PostgreSQL"""
    
    def __init__(self, db_path_or_url: str, schema: Optional[str] = None):
        """
        Инициализация async подключения к БД
        
        Args:
            db_path_or_url: Путь к SQLite файлу или URL для PostgreSQL
            schema: Схема PostgreSQL (для разделения данных разных сервисов)
        """
        self.db_path_or_url = db_path_or_url
        self.db_type = DB_TYPE
        self.schema = schema
        
        if self.db_type == "postgres" and not ASYNCPG_AVAILABLE:
            if not AIOSQLITE_AVAILABLE:
                raise RuntimeError("PostgreSQL выбран, но asyncpg не установлен. Установите: pip install asyncpg")
        elif not AIOSQLITE_AVAILABLE:
            raise RuntimeError("aiosqlite не установлен. Установите: pip install aiosqlite")
    
    @asynccontextmanager
    async def get_connection(self):
        """Асинхронный контекстный менеджер для получения подключения"""
        if self.db_type == "postgres" and ASYNCPG_AVAILABLE:
            # PostgreSQL async
            conn = await asyncpg.connect(self.db_path_or_url)
            try:
                if self.schema:
                    await conn.execute(f"SET search_path TO {self.schema}, public")
                yield conn
            finally:
                await conn.close()
        else:
            # SQLite async
            conn = await aiosqlite.connect(self.db_path_or_url)
            try:
                yield conn
            finally:
                await conn.close()
    
    async def execute(self, query: str, params: Optional[Union[tuple, dict, List]] = None):
        """
        Выполняет SQL запрос асинхронно
        
        Args:
            query: SQL запрос (адаптируется автоматически)
            params: Параметры запроса
        
        Returns:
            Результат выполнения запроса
        """
        # Адаптируем SQL для PostgreSQL
        if self.db_type == "postgres":
            query = DatabaseConnection._adapt_sql_for_postgres(query)
        
        async with self.get_connection() as conn:
            if self.db_type == "postgres" and ASYNCPG_AVAILABLE:
                if params:
                    rows = await conn.fetch(query, *params if isinstance(params, (tuple, list)) else params)
                else:
                    rows = await conn.fetch(query)
                return [dict(row) for row in rows]
            else:
                # SQLite async
                if params:
                    cursor = await conn.execute(query, params if isinstance(params, tuple) else tuple(params))
                else:
                    cursor = await conn.execute(query)
                await conn.commit()
                rows = await cursor.fetchall()
                # Преобразуем в список словарей
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                return [dict(zip(columns, row)) for row in rows]
    
    async def fetchone(self, query: str, params: Optional[Union[tuple, dict, List]] = None):
        """Выполняет запрос асинхронно и возвращает одну строку"""
        if self.db_type == "postgres":
            query = DatabaseConnection._adapt_sql_for_postgres(query)
        
        async with self.get_connection() as conn:
            if self.db_type == "postgres" and ASYNCPG_AVAILABLE:
                if params:
                    row = await conn.fetchrow(query, *params if isinstance(params, (tuple, list)) else params)
                else:
                    row = await conn.fetchrow(query)
                return dict(row) if row else None
            else:
                # SQLite async
                if params:
                    cursor = await conn.execute(query, params if isinstance(params, tuple) else tuple(params))
                else:
                    cursor = await conn.execute(query)
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    return dict(zip(columns, row))
                return None
    
    async def fetchall(self, query: str, params: Optional[Union[tuple, dict, List]] = None):
        """Выполняет запрос асинхронно и возвращает все строки"""
        return await self.execute(query, params)


# Async функции-обертки
async def async_execute_query(db_path_or_url: str, query: str, params: Optional[Union[tuple, dict, List]] = None, schema: Optional[str] = None):
    """Выполняет SQL запрос асинхронно"""
    db = AsyncDatabaseConnection(db_path_or_url, schema)
    return await db.execute(query, params)


async def async_fetch_one(db_path_or_url: str, query: str, params: Optional[Union[tuple, dict, List]] = None, schema: Optional[str] = None):
    """Выполняет запрос асинхронно и возвращает одну строку"""
    db = AsyncDatabaseConnection(db_path_or_url, schema)
    return await db.fetchone(query, params)


async def async_fetch_all(db_path_or_url: str, query: str, params: Optional[Union[tuple, dict, List]] = None, schema: Optional[str] = None):
    """Выполняет запрос асинхронно и возвращает все строки"""
    db = AsyncDatabaseConnection(db_path_or_url, schema)
    return await db.fetchall(query, params)
