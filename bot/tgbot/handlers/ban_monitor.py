import asyncio
import logging
import os

from aiogram import Bot
from aiogram.utils.exceptions import BadRequest

from bot.tgbot.databases.database import DatabaseConnection
from config import BASE_DIR, MAIN_DB_PATH, load_config, logger_bot

from dotenv import load_dotenv

load_dotenv()


# Настройки
config = load_config(os.path.join(BASE_DIR, ".env"))
bot = Bot(token=config.tg_bot.token)

HOST_TURN = os.getenv("HOST_TURN", "False").strip().lower() == "true"
if HOST_TURN:
    channels_ids = os.getenv("BAN_CHANNELS", "").split(",")
else:
    channels_ids = os.getenv("TEST_BAN_CHANNELS", "").split(",")


def get_users_by_status(pay_status):
    """Получаем user_id по статусу оплаты"""
    try:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main")
        rows = db.fetchall("SELECT user_id FROM users WHERE pay_status::int = %s", (pay_status,))
        users = set()
        for row in rows:
            if isinstance(row, dict):
                user_id = row.get('user_id')
            else:
                user_id = row[0] if row else None
            if user_id:
                users.add(int(user_id))
        return users
    except Exception as e:
        logger_bot.error(
            f"Ошибка получения пользователей с pay_status {pay_status}: {e}"
        )
        return set()


async def ban_user(user_id):
    for channel_id in channels_ids:
        try:
            await bot.ban_chat_member(
                chat_id=int(channel_id),
                user_id=user_id,
            )
            logger_bot.info(f"Забанен пользователь {user_id} в группе/канале с ID: {channel_id}")
        except BadRequest as e:
            logger_bot.warning(f"Не удалось забанить {user_id}: {e}, в группе/канале с ID: {channel_id}")
        except Exception as e:
            logger_bot.error(f"Ошибка при бане {user_id}: {e}")


async def unban_user(user_id):
    """Разбаниваем пользователя ботом aiogram, без логирования ошибок"""
    for channel_id in channels_ids:
        try:
            await bot.unban_chat_member(
                chat_id=int(channel_id),
                user_id=user_id,
                only_if_banned=True,
            )
        except BadRequest:
            pass  # Игнорируем все ошибки


processed_bans = set()
processed_unbans = set()


async def check_and_manage_users():
    global processed_bans, processed_unbans
    try:
        current_unban_users = get_users_by_status(1)  # те, кто оплатил
        current_ban_users = get_users_by_status(0)  # те, кто не оплатил

        # Находим новых для разбана
        new_unban_users = current_unban_users - processed_unbans
        for user_id in new_unban_users:
            await unban_user(user_id)
        processed_unbans = current_unban_users  # запоминаем текущее состояние

        # Находим новых для бана
        new_ban_users = current_ban_users - processed_bans
        for user_id in new_ban_users:
            await ban_user(user_id)
        processed_bans = current_ban_users  # запоминаем текущее состояние

    except Exception as e:
        logger_bot.error(f"Ошибка в check_and_manage_users: {e}")


async def run_ban_monitor():
    """Запуск каждые 300 сек"""
    while True:
        await check_and_manage_users()
        await asyncio.sleep(300)


if __name__ == "__main__":
    asyncio.run(run_ban_monitor())
