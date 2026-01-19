import asyncio
from typing import Union

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from yookassa import Configuration, Payment

from bot.tgbot.databases.pay_db import createPayment  # если используешь
from bot.tgbot.databases.pay_db import *
from config import logger_bot


# НАСТРОЙКИ YOOKASSA
Configuration.configure("1108748", "live_7-DWXPLohPIAHRznDkb4AysalOQLuiGfHLi_WwSbx98")


# Клавиатура с оплатой
def check_type_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🏢 Юр. лицо", callback_data="check_jur"),
        InlineKeyboardButton("👤 Физ. лицо", callback_data="check_fiz"),
        InlineKeyboardButton("🏠 Недвижимость", callback_data="check_realty"),
    )
    return markup


def irbis_pay_keyboard(payment_link):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💳 Оплатить 200 руб", url=payment_link))
    return markup


# Генерация платежа
def genPaymentYookassa_Irbis(price="200.00", description="Проверка Irbis", purpose="irbis_check", user_id=None):
    price = price
    bot_username = "DomosproBot"  # <--- укажи свой username
    return_url = f"https://t.me/{bot_username}"
    metadata = {
        "purpose": purpose,
    }
    if user_id:
        metadata["user_id"] = str(user_id)
    res = Payment.create(
        {
            "amount": {"value": price, "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": description,
            "metadata": metadata,
            "receipt": {
                "customer": {
                    "full_name": "Покупатель Irbis",
                    "email": "test@example.com",  # реальный email обязателен!
                    "phone": "79999999999",  # реальный телефон обязателен!
                },
                "items": [
                    {
                        "description": description,
                        "quantity": "1.00",
                        "amount": {"value": price, "currency": "RUB"},
                        "vat_code": "1",  # укажи правильную ставку НДС!
                        "payment_mode": "full_payment",
                        "payment_subject": "service",
                    }
                ],
            },
        }
    )
    payment_id = res.id
    payment_link = res.confirmation.confirmation_url
    return payment_id, payment_link


# Проверка оплаты
def checkPaymentYookassa(id):
    res = Payment.find_one(id)
    return res.status


# Отмена оплаты
def cancelPaymentYookassa(id):
    res = Payment.cancel(id)
    return res.status


async def wait_for_payment(payment_id, cb: CallbackQuery):
    """Устаревшая функция - теперь используем webhook от YooKassa"""
    logger_bot.info(f"Проверяем платёж с payment_id={payment_id} (одноразовая проверка)")
    status = checkPaymentYookassa(payment_id)
    if status == "succeeded":
        logger_bot.info("✅ Оплата прошла успешно! Доступ к IRBIS открыт.")
        await cb.message.answer("✅ Оплата прошла успешно! Доступ к IRBIS открыт.")
        await cb.message.answer(
            "Выберите, кого вы хотите проверить:", reply_markup=check_type_keyboard()
        )
        return
    else:
        logger_bot.info(f"⏳ Платеж ещё обрабатывается. Уведомление придёт автоматически после успешной оплаты.")
        await cb.message.answer(
            "⏳ Платеж ещё обрабатывается. Уведомление придёт автоматически после успешной оплаты."
        )


# Хэндлер /irbis
async def irbis_command(update: Union[Message, CallbackQuery], state: FSMContext):
    if isinstance(update, Message):
        user_id = update.from_user.id
        username = update.from_user.username
        message = update
    else:  # CallbackQuery
        user_id = update.from_user.id
        username = update.from_user.username
        message = update.message

    banned = getBannedUserId(user_id)
    if banned == 0:
        payed = getUserPay(user_id)
        if payed == 1:
            if username is None:
                await message.answer(
                    """
    Для корректной работы необходимо в настройках изменить имя пользователя!
    Как это сделать:
    Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
    После изменения @username войдите в бот по ссылке еще раз и нажмите /start
    """
                )
            else:
                if user_id == "779889025" or user_id == 779889025:
                    payment_id, payment_link = genPaymentYookassa_Irbis(price="1.00", purpose="irbis_check", user_id=user_id)
                else:
                    payment_id, payment_link = genPaymentYookassa_Irbis(purpose="irbis_check", user_id=user_id)
                createPayment(payment_id, 200, message.from_user.id)
                await state.update_data(payment_id=payment_id)

                await message.answer(
                    "💡 <b>Стоимость одной проверки — 200 руб</b>.\n\n"
                    "Нажмите кнопку «Оплатить 200 руб.» для оплаты.\n"
                    "После успешной оплаты вы получите уведомление автоматически.",
                    reply_markup=irbis_pay_keyboard(payment_link),
                    parse_mode="HTML",
                )
                logger_bot.info(
                    f"Пользователь {user_id}, сформировал ссылку на оплату irbis: {payment_link}"
                )
        else:
            await message.answer("⭕ Сначала оплатите подписку!")


async def handle_check_jur(call: types.CallbackQuery):
    user_id = call.from_user.id
    message_id = call.message.message_id
    url = f"https://neurochief.pro/org_check?user_id={user_id}&message_id={message_id}"
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            text="📝 Заполнить данные для проверки юр. лица",
            web_app=WebAppInfo(url=url),
        )
    )
    await call.message.edit_text(
        "Для продолжения заполните форму по кнопке ниже:", reply_markup=markup
    )


async def handle_check_fiz(call: types.CallbackQuery):
    user_id = call.from_user.id
    message_id = call.message.message_id
    url = (
        f"https://neurochief.pro/people_check?user_id={user_id}&message_id={message_id}"
    )
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            text="📝 Заполнить данные для проверки физ. лица",
            web_app=WebAppInfo(url=url),
        )
    )
    await call.message.edit_text(
        "Для продолжения заполните форму по кнопке ниже:", reply_markup=markup
    )


async def handle_check_realty(call: types.CallbackQuery):
    user_id = call.from_user.id
    message_id = call.message.message_id
    url = (
        f"https://neurochief.pro/house_check?user_id={user_id}&message_id={message_id}"
    )
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            text="📝 Заполнить данные для проверки недвижимости",
            web_app=WebAppInfo(url=url),
        )
    )
    await call.message.edit_text(
        "Для продолжения заполните форму по кнопке ниже:", reply_markup=markup
    )


def register_irbis(dp: Dispatcher):
    dp.register_message_handler(irbis_command, commands=["irbis"], state="*")
    dp.register_callback_query_handler(
        handle_check_jur, lambda c: c.data == "check_jur", state="*"
    )
    dp.register_callback_query_handler(
        handle_check_fiz, lambda c: c.data == "check_fiz", state="*"
    )
    dp.register_callback_query_handler(
        handle_check_realty, lambda c: c.data == "check_realty", state="*"
    )
