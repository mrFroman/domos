import aiohttp
import secrets
import sqlite3

from aiogram import Dispatcher
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup


from config import ADVERT_TOKENS_DB_PATH, logger_bot


def _token_exists(token: str) -> bool:
    """Returns True if token already stored in advert DB."""
    with sqlite3.connect(ADVERT_TOKENS_DB_PATH) as conn:
        cur = conn.execute(
            "SELECT 1 FROM tokens WHERE token = ? LIMIT 1",
            (token,),
        )
        return cur.fetchone() is not None


def _generate_unique_token() -> str:
    """Generate token and ensure uniqueness in advert DB."""
    while True:
        token = secrets.token_urlsafe(16)
        if not _token_exists(token):
            return token


async def start_advertisement_process(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    token = _generate_unique_token()
    payload = {
        "user_id": user_id,
        "token": token,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                # TODO Вернуть старую ссылку после тестов
                # "http://localhost:8001/api/save_advert_data",
                "https://neurochief.pro/api/save_advert_data",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    await callback_query.message.answer(
                        "❌ Не удалось сформировать ссылку для заявки на рекламу"
                    )
                    logger_bot.error(
                        f"❌ Не удалось сформировать ссылку для заявки на рекламу: {text}"
                    )
                    return
    except Exception as e:
        logger_bot.error(f"❌ Ошибка: {e}")
        await callback_query.message.answer(f"❌ Ошибка: {str(e)}")

    # TODO Изменить путь после тестов
    #     form_url = f"http://localhost:8001/api/send_advert_form/{token}"
    #     await callback_query.message.answer(
    #         text="""
    #         В данной форме нужно указать количество необходимых вам размещений на различных порталах.
    # Внимательно прочтите заголовок и ответьте на каждый вопрос.\n
    # Если размещения на сайте вам не нужны, то укажите "0".\n
    # Реклама лотов вне Свердловской области настраивается и оплачивается индивидуально с офис-менеджером
    #     """
    #     )
    # await callback_query.message.reply(f"Перейдите по ссылке: {form_url}")
    form_url = f"https://neurochief.pro/api/send_advert_form/{token}"
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✏️ Заполнить форму заявки на рекламу", url=form_url)
    )
    await callback_query.message.answer(
        text="""
        В данной форме нужно указать количество необходимых вам размещений на различных порталах.
Внимательно прочтите заголовок и ответьте на каждый вопрос.
Если размещения на сайте вам не нужны, то укажите цифру ноль "0".
Реклама лотов вне Свердловской области настраивается и оплачивается индивидуально с офис-менеджером
    """,
        reply_markup=keyboard,
    )


def register_advertisement_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(
        start_advertisement_process,
        lambda c: c.data == "advertisement",
        state=None,
    )
