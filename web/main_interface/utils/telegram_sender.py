"""
Утилита для отправки сообщений через Telegram бота
"""
import os
import sys
import asyncio
import logging
from aiogram import Bot

logger = logging.getLogger(__name__)

# Для aiogram 2.x исключения находятся в другом месте
try:
    from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
except ImportError:
    # Для aiogram 2.x используем базовые исключения
    TelegramBadRequest = Exception
    TelegramAPIError = Exception

# Токен бота для отправки кодов авторизации
# ВАЖНО: Используем ТОЛЬКО этот токен для отправки кодов авторизации
AUTH_BOT_TOKEN = "8509123105:AAFCegXrWnq0GuPJqFOB8bMm9O04S9Rtmnc"

def get_bot_token():
    """Получить токен бота для отправки кодов авторизации"""
    # ВСЕГДА используем хардкод токен для авторизации
    # Это гарантирует, что коды будут отправляться через правильного бота
    logger.info(f"Используется токен для авторизации: {AUTH_BOT_TOKEN[:15]}...")
    return AUTH_BOT_TOKEN


async def send_code_to_user_async(phone: str, code: str, telegram_user_id: int = None):
    """
    Асинхронная отправка кода подтверждения пользователю через Telegram бота
    
    Args:
        phone: Номер телефона пользователя
        code: Код подтверждения
        telegram_user_id: Telegram ID пользователя (если известен)
    
    Returns:
        bool: True если сообщение отправлено успешно, False в противном случае
    """
    if not telegram_user_id:
        logger.warning(f"Не указан telegram_user_id для номера {phone}")
        return False
    
    try:
        # Получаем актуальный токен каждый раз (на случай изменения)
        token = get_bot_token()
        logger.info(f"Отправка кода через бота с токеном: {token[:15]}... (ID пользователя: {telegram_user_id})")
        bot = Bot(token=token)
        message_text = (
            f"🔐 Код подтверждения для входа в Domos\n\n"
            f"Ваш код: <b>{code}</b>\n\n"
            f"Код действителен в течение 5 минут.\n"
            f"Не сообщайте этот код никому!"
        )
        
        await bot.send_message(
            chat_id=telegram_user_id,
            text=message_text,
            parse_mode="HTML"
        )
        
        await bot.session.close()
        logger.info(f"Код отправлен пользователю {telegram_user_id} для номера {phone}")
        return True
        
    except Exception as e:
        error_msg = str(e)
        # Проверяем тип ошибки по сообщению для aiogram 2.x
        if "chat not found" in error_msg.lower() or "user not found" in error_msg.lower():
            logger.error(f"Пользователь не найден или не подписан на бота: {e}")
        elif "blocked" in error_msg.lower():
            logger.error(f"Пользователь заблокировал бота: {e}")
        else:
            logger.error(f"Ошибка при отправке кода: {e}")
        return False


def send_code_to_user(phone: str, code: str, telegram_user_id: int = None):
    """
    Синхронная обертка для отправки кода подтверждения
    
    Args:
        phone: Номер телефона пользователя
        code: Код подтверждения
        telegram_user_id: Telegram ID пользователя (если известен)
    
    Returns:
        bool: True если сообщение отправлено успешно, False в противном случае
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(send_code_to_user_async(phone, code, telegram_user_id))


def find_telegram_id_by_phone(phone: str):
    """
    Найти Telegram ID пользователя по номеру телефона в базе данных
    
    Args:
        phone: Номер телефона (может быть в разных форматах)
    
    Returns:
        int или None: Telegram ID пользователя или None если не найден
    """
    import sys
    import os
    
    # Добавляем путь к модулям бота
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    
    try:
        from bot.tgbot.databases.pay_db import get_user_by_user_id
        from bot.tgbot.databases.database import DatabaseConnection
        from config import MAIN_DB_PATH, DB_TYPE
        
        # Нормализуем номер телефона (убираем все кроме цифр)
        phone_clean = ''.join(filter(str.isdigit, phone))
        
        # Ищем пользователя в базе данных
        # Проверяем разные форматы номера
        phone_variants = [
            phone_clean,
            phone_clean[-10:],  # Последние 10 цифр
            f"+7{phone_clean[-10:]}",  # С +7
            f"8{phone_clean[-10:]}",  # С 8
        ]
        
        # Используем схему main для PostgreSQL
        schema = "main" if DB_TYPE == "postgres" else None
        db = DatabaseConnection(MAIN_DB_PATH, schema=schema)
        
        # Сначала проверяем, есть ли поле phone в таблице users
        # Пробуем найти пользователя по номеру телефона
        # Проверяем разные варианты формата номера
        for phone_variant in phone_variants:
            try:
                # Для PostgreSQL используем ILIKE, для SQLite - LIKE
                if DB_TYPE == "postgres":
                    # Пробуем найти по полю phone
                    try:
                        query = """
                            SELECT user_id FROM main.users 
                            WHERE phone ILIKE %s OR phone ILIKE %s
                            LIMIT 1
                        """
                        results = db.execute(query, (f"%{phone_variant}%", f"%{phone_clean}%"))
                        if results:
                            user_id = results[0].get('user_id') if isinstance(results[0], dict) else results[0][0]
                            if user_id:
                                logger.info(f"Найден пользователь по phone: user_id={user_id}, phone={phone_variant}")
                                return int(user_id)
                    except Exception as e:
                        logger.debug(f"Поле phone не найдено или ошибка: {e}")
                    
                    # Альтернативный поиск: ищем по username, если там может быть номер телефона
                    try:
                        query = """
                            SELECT user_id FROM main.users 
                            WHERE username LIKE %s OR username LIKE %s
                            LIMIT 1
                        """
                        results = db.execute(query, (f"%{phone_variant}%", f"%{phone_clean}%"))
                        if results:
                            user_id = results[0].get('user_id') if isinstance(results[0], dict) else results[0][0]
                            if user_id:
                                logger.info(f"Найден пользователь по username: user_id={user_id}, phone={phone_variant}")
                                return int(user_id)
                    except Exception as e:
                        logger.debug(f"Ошибка поиска по username: {e}")
                else:
                    # SQLite
                    try:
                        query = """
                            SELECT user_id FROM users 
                            WHERE phone LIKE ? OR phone LIKE ?
                            LIMIT 1
                        """
                        results = db.execute(query, (f"%{phone_variant}%", f"%{phone_clean}%"))
                        if results:
                            user_id = results[0].get('user_id') if isinstance(results[0], dict) else results[0][0]
                            if user_id:
                                logger.info(f"Найден пользователь по phone: user_id={user_id}, phone={phone_variant}")
                                return int(user_id)
                    except Exception as e:
                        logger.debug(f"Поле phone не найдено или ошибка: {e}")
                    
                    # Альтернативный поиск по username
                    try:
                        query = """
                            SELECT user_id FROM users 
                            WHERE username LIKE ? OR username LIKE ?
                            LIMIT 1
                        """
                        results = db.execute(query, (f"%{phone_variant}%", f"%{phone_clean}%"))
                        if results:
                            user_id = results[0].get('user_id') if isinstance(results[0], dict) else results[0][0]
                            if user_id:
                                logger.info(f"Найден пользователь по username: user_id={user_id}, phone={phone_variant}")
                                return int(user_id)
                    except Exception as e:
                        logger.debug(f"Ошибка поиска по username: {e}")
                        
            except Exception as e:
                logger.debug(f"Ошибка поиска по варианту {phone_variant}: {e}")
                continue
        
        logger.warning(f"Пользователь с номером {phone} не найден в базе данных")
        return None
        
    except Exception as e:
        logger.error(f"Ошибка при поиске пользователя по номеру телефона: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
