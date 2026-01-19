import asyncio
import calendar
import logging
import os
import sqlite3
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BASE_DIR, MAIN_DB_PATH, YEKATERINBURG_TZ, load_config, logger_bot


# Функция для получения пользователей с pay_status = 1
def get_paying_users(db_path: str):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE pay_status = 1')
        users = cursor.fetchall()
        conn.close()
        return [user[0] for user in users]
        # return [779889025]  # Возвращаем список ID пользователей
    except Exception as e:
        logger_bot.error(f"Error getting paying users from DB: {e}")
        return []


async def send_monthly_survey(bot: Bot, user_id: int):
    try:
        # Замените на реальный URL формы
        survey_url = "https://docs.google.com/forms/d/e/1FAIpQLSdrK0jWZXi1FEWUepYC_M_XblO8EIhIwrYL9_V0G_mLVC2TXw/viewform?usp=header"
        message_text = (
            "📅 Привет! Сегодня последний день месяца.\n\n"
            "Пожалуйста, заполните ежемесячный опрос о вашей работе. "
            "Это займет всего 2 минуты!\n\n"
            "Спасибо за ваше участие! 🙏"
        )

        button = InlineKeyboardButton(text="📝 Заполнить опрос", url=survey_url)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])

        await bot.send_message(user_id, message_text, reply_markup=keyboard)

        logger_bot.info(f"Monthly survey sent to user {user_id}")
    except Exception as e:
        logger_bot.error(
            f"Failed to send monthly survey to user {user_id}: {e}")


def is_last_day_of_month():
    today = datetime.now()
    last_day = calendar.monthrange(today.year, today.month)[1]
    return today.day == last_day


async def check_and_send_survey():
    config = load_config(os.path.join(BASE_DIR, ".env"))
    bot = Bot(token=config.tg_bot.token, parse_mode='HTML')

    if is_last_day_of_month():
        # Получаем всех оплативших пользователей
        db_path = MAIN_DB_PATH
        paying_users = get_paying_users(db_path)

        if not paying_users:
            logger_bot.warning(
                "Нет пользователей с payment_status = 1 в data.db")
            return

        logger_bot.info(
            f"Найдено {len(paying_users)} пользователей с payment_status = 1 в data.db")

    # Отправляем каждому пользователю
    for user_id in paying_users:
        try:
            await send_monthly_survey(bot, user_id)
            await asyncio.sleep(1)
        except Exception as e:
            logger_bot.error(
                f"Ошибка отправки сообщения пользователю {user_id}: {e}")
            continue


async def scheduler():
    while True:
        now = datetime.now(YEKATERINBURG_TZ)

        # Проверяем в 10 утра по Екатеринбургу
        if now.hour == 10 and now.minute == 0:
            await check_and_send_survey()

        # Спим до следующей минуты
        next_check = now + timedelta(minutes=1)
        await asyncio.sleep((next_check - now).total_seconds())

if __name__ == '__main__':
    try:
        asyncio.run(scheduler())
    except (KeyboardInterrupt, SystemExit):
        logger_bot.error("Мониторинг ежемесячного опроса остановлен!")
