import asyncio
import os
import requests
import sys
import time
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from subprocess import Popen

# Добавляем корень проекта в sys.path для корректного импорта локального config.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage2
import django
from config import BASE_DIR

WEB_DIR = os.path.join(BASE_DIR, "web")

# if WEB_DIR not in sys.path:
#     sys.path.append(WEB_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.web.settings")
django.setup()

from bot.tgbot.filters.admin import AdminFilter
# from bot.tgbot.handlers.admin import register_admin
from bot.tgbot.handlers.advert_new import register_advertisement_handlers
from bot.tgbot.handlers.advert_admin import register_advert_admin_handlers
from bot.tgbot.handlers.audio_saver import register_audio_saver_handlers
from bot.tgbot.handlers.advert import register_advert_handlers
from bot.tgbot.handlers.contacts import register_contacts
from bot.tgbot.handlers.chat_join_request import register_chat_join_requests
from bot.tgbot.handlers.dogovor import register_dogovor
from bot.tgbot.handlers.eventsmenu import regevents
from bot.tgbot.handlers.feedback import register_feedback
from bot.tgbot.handlers.frst_day import register_frstday
from bot.tgbot.handlers.helpful import register_helpful
from bot.tgbot.handlers.image_handler import register_image_generator_handlers
from bot.tgbot.handlers.invitefriend import register_invite
from bot.tgbot.handlers.needed_access import register_needed
from bot.tgbot.handlers.office_access import register_office_access
from bot.tgbot.handlers.payment import register_payment
from bot.tgbot.handlers.rieltorslist import register_rieltorslist
from bot.tgbot.handlers.rent_meeting import register_meeting
from bot.tgbot.handlers.rules import register_rules
from bot.tgbot.handlers.searchuser import register_searchuser
from bot.tgbot.handlers.settings import register_settings
from bot.tgbot.handlers.lawyer import register_lawyer_handlers
from bot.tgbot.handlers.payment_irbis import register_irbis
from bot.tgbot.handlers.request_from_db import register_request_from_db
from bot.tgbot.handlers.user import register_user
from bot.tgbot.handlers.whatsup import register_whatsup
from bot.tgbot.handlers.yandex_gpt_handler import register_yandex_gpt
from bot.tgbot.middlewares.environment import EnvironmentMiddleware
from bot.tgbot.services.parse_chat_message import (
    register_usefull_messages_saver_handlers,
)
from config import BASE_DIR, load_config, logger_bot


config = load_config(os.path.join(BASE_DIR, ".env"))

storage = RedisStorage2() if config.tg_bot.use_redis else MemoryStorage()
bot = Bot(token=config.tg_bot.token, parse_mode="HTML")
dp = Dispatcher(bot, storage=storage)

bot["config"] = config


def register_all_middlewares(dp, config):
    dp.setup_middleware(EnvironmentMiddleware(config=config))


def register_all_filters(dp):
    dp.filters_factory.bind(AdminFilter)


def register_all_handlers(dp):
    register_irbis(dp)
    # register_admin(dp)
    register_user(dp)
    register_lawyer_handlers(dp)
    register_advert_handlers(dp)
    register_frstday(dp)
    register_needed(dp)
    register_dogovor(dp)
    register_office_access(dp)
    register_whatsup(dp)
    register_meeting(dp)
    register_rules(dp)
    register_helpful(dp)
    register_feedback(dp)
    register_rieltorslist(dp)
    register_settings(dp)
    register_payment(dp)
    register_searchuser(dp)
    register_invite(dp)
    register_contacts(dp)
    regevents(dp)
    register_image_generator_handlers(dp)
    register_yandex_gpt(dp)
    register_audio_saver_handlers(dp)
    register_request_from_db(dp)
    register_advertisement_handlers(dp)
    register_advert_admin_handlers(dp)
    register_usefull_messages_saver_handlers(dp)
    register_chat_join_requests(dp)


async def run_parse_nmarket():
    """Запуск парсера nmarket.pro"""
    try:
        Popen([sys.executable, "-m", "bot.tgbot.services.parse_nmarket"])
        logger_bot.info(
            f'[{datetime.now().strftime("%Y-%m-%d %H:%M")}] Парсер сайта nmarket.pro активирован'
        )
    except Exception as e:
        logger_bot.error(f"Ошибка при запуске парсера nmarket.pro: {e}")


async def scheduler_start():
    """Запуск планировщика задач"""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_parse_nmarket, "cron", day_of_week="sat", hour=1, minute=0)
    logger_bot.info("Планировщик запущен")
    scheduler.start()


async def start_monitors():
    try:
        Popen([sys.executable, "-m", "bot.tgbot.handlers.tsmonitor"])
        logger_bot.info("Мониторинг подписок активирован")

        #Popen([sys.executable, "-m", "bot.tgbot.handlers.payment_monitor"])
        #logger_bot.info("Мониторинг оплат активирован")

        #Popen([sys.executable, "-m", "bot.tgbot.handlers.notifymonitor"])
        #logger_bot.info("Мониторинг оплаты подписки активирован")

        #Popen([sys.executable, "-m", "bot.tgbot.handlers.eventsmonitor"])
        #logger_bot.info("Мониторинг событий активирован")

        #Popen([sys.executable, "-m", "bot.tgbot.handlers.ban_monitor"])
        #logger_bot.info("Мониторинг бана в канале активирован")

       #Popen([sys.executable, "-m", "bot.tgbot.services.monthly_anket"])
        #logger_bot.info("Мониторинг ежемесячного опроса активирован")

        #Popen([sys.executable, "-m", "bot.tgbot.services.recurrent_payments"])
        #logger_bot.info("Мониторинг рекуррентных платежей активирован")

        #Popen([sys.executable, "-m", "bot.tgbot.services.parse_messages"])
        
        logger_bot.info("Парсер сообщений из каналов активирован")
    except Exception as e:
        logger_bot.error(f"Ошибка при запуске мониторингов: {e}")


async def heartbeat():
    """Фоновая задача — раз в минуту проверяет работу бота и шлёт сообщение"""
    while True:
        try:
            # Проверка доступности Telegram API
            me = await bot.get_me()
            bot_name = me.username

            # Если всё ок — отправляем heartbeat
            text = f"✅ Бот @{bot_name} работает. Количество активных сессий в базе: {len(storage.data)}"
            requests.get(
                f"https://api.telegram.org/bot{config.tg_bot.token}/sendMessage?chat_id={-1002294501707}&text={text}&parse_mode=HTML"
            )

        except Exception as e:
            # Если что-то не сработало — логируем и шлём сообщение об ошибке
            logger_bot.error(f"Ошибка при heartbeat: {e}")
            try:
                text = f"❌ Heartbeat ошибка: {e}"
                requests.get(
                    f"https://api.telegram.org/bot{config.tg_bot.token}/sendMessage?chat_id={-1002294501707}&text={text}&parse_mode=HTML"
                )
            except Exception:
                pass  # если даже уведомление не ушло, пропускаем

        await asyncio.sleep(60)  # проверка раз в минуту


async def main():
    register_all_middlewares(dp, config)
    register_all_filters(dp)
    register_all_handlers(dp)

    # Запускаем планировщик
    # TODO Вернуть после тестов
    await scheduler_start()

    # start
    try:
        text = "Бот запущен"
        requests.get(
            f"https://api.telegram.org/bot{config.tg_bot.token}/sendMessage?chat_id={-1002294501707}&text={text}&parse_mode=HTML"
        )

        asyncio.create_task(start_monitors())
        asyncio.create_task(heartbeat())
        await dp.start_polling(
            dp,
            allowed_updates=[
                "message",
                "callback_query",
                "channel_post",
                "chat_join_request",
            ],
        )
    finally:
        logger_bot.error("Бот остановлен!")
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        text = f"Бот остановлен! Ошибка: {error}"
        requests.get(
            f"https://api.telegram.org/bot{config.tg_bot.token}/sendMessage?chat_id={-1002294501707}&text={text}&parse_mode=HTML"
        )
        logger_bot.error(f"Бот остановлен! Ошибка: {error}")
