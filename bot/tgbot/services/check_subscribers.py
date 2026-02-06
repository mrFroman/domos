import asyncio
import os
import logging
from aiogram import Bot, types
from aiogram.utils.exceptions import Unauthorized, BadRequest
from pathlib import Path
from dotenv import load_dotenv

from bot.tgbot.databases.database import AsyncDatabaseConnection, DB_TYPE
from config import MAIN_DB_PATH

path = str(Path(__file__).parents[2])

load_dotenv()

# --- Настройки ---
API_TOKEN = os.getenv("BOT_TOKEN")  # 🔁 Заменить на токен бота
CHANNEL_ID = int(os.getenv("PAID_CHANNEL"))   # 🔁 Заменить на ID канала (НЕ ссылку!)

NOTIFY_TEXT = (
    "Дорогой друг!\n\n"
    "У нас есть канал, в котором выходят трансляции с важной информацией. "
    "Чтобы получать максимум пользы от нашего сообщества — пожалуйста, подпишись: "
    "https://t.me/+VI_Vtc-hlC4zNGZi"
)

# --- Логирование ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# --- Основной процесс ---
async def send_subscription_reminders():
    bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)

    try:
        # Подключение к БД
        db = AsyncDatabaseConnection(MAIN_DB_PATH, schema="main")

        # Получаем пользователей с активной подпиской
        # Для PostgreSQL используем ::int, для SQLite используем CAST
        if DB_TYPE == "postgres":
            users = await db.fetchall("SELECT user_id FROM users WHERE pay_status::int = 1")
        else:
            users = await db.fetchall("SELECT user_id FROM users WHERE CAST(pay_status AS INTEGER) = 1")
        logging.info(f"Найдено активных пользователей: {len(users)}")

        for user_row in users:
            if isinstance(user_row, dict):
                user_id = user_row.get('user_id')
            else:
                user_id = user_row[0] if user_row else None
            
            if not user_id:
                continue
                
            try:
                # Проверка подписки
                member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)

                if member.status not in ["member", "administrator", "creator"]:
                    # Не подписан — отправить сообщение
                    try:
                        await bot.send_message(chat_id=user_id, text=NOTIFY_TEXT)
                        logging.info(f"Уведомление отправлено пользователю {user_id}")
                    except Unauthorized:
                        logging.warning(f"Бот не может написать пользователю {user_id} — доступ запрещён")
                    except BadRequest as e:
                        logging.error(f"BadRequest при отправке пользователю {user_id}: {e}")
            except Exception as e:
                logging.error(f"Ошибка при проверке подписки для {user_id}: {e}")

    finally:
        await bot.session.close()


# --- Запуск ---
if __name__ == "__main__":
    asyncio.run(send_subscription_reminders())

