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
    markup.add(
        InlineKeyboardButton(
            "Подтвердить оплату", callback_data="confirm_irbis_payment"
        )
    )
    return markup


# Генерация платежа
def genPaymentYookassa_Irbis(price="200.00", description="Проверка Irbis"):
    price = price
    bot_username = "DomosproBot"  # <--- укажи свой username
    return_url = f"https://t.me/{bot_username}"
    res = Payment.create(
        {
            "amount": {"value": price, "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": description,
            "metadata": {
                "purpose": "irbis_check",
            },
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
    logger_bot.info(f"Проверяем платёж с payment_id={payment_id}")
    status = checkPaymentYookassa(payment_id)
    if status == "succeeded":
        logger_bot.info("✅ Оплата прошла успешно! Доступ к IRBIS открыт.")
        await cb.message.answer("✅ Оплата прошла успешно! Доступ к IRBIS открыт.")
        await cb.message.answer(
            "Выберите, кого вы хотите проверить:", reply_markup=check_type_keyboard()
        )
        return
    else:
        logger_bot.error(f"❌ Оплата платежа: {payment_id} ещё не прошла.")
        await cb.message.answer("❌ Оплата ещё не прошла, попробуйте чуть позже.")


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
                    payment_id, payment_link = genPaymentYookassa_Irbis(price="1.00")
                else:
                    payment_id, payment_link = genPaymentYookassa_Irbis()
                createPayment(payment_id, 200, message.from_user.id)
                await state.update_data(payment_id=payment_id)

                await message.answer(
                    "💡 <b>Стоимость одной проверки — 200 руб</b>.\n\n"
                    "Нажмите кнопку «Оплатить 200 руб.»,,\n"
                    "а затем подтвердите оплату.",
                    reply_markup=irbis_pay_keyboard(payment_link),
                    parse_mode="HTML",
                )
                logger_bot.info(
                    f"Пользователь {user_id}, сформировал ссылку на оплату irbis: {payment_link}"
                )
        else:
            await message.answer("⭕ Сначала оплатите подписку!")


async def confirm_payment_irbis(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    payment_id = data.get("payment_id")
    if not payment_id:
        logger_bot.error(f"❌ Платёж пользователя: {cb.from_user.id} не найден.")
        await cb.message.answer("❌ Не найден платеж. Попробуйте ещё раз.")
        return
    asyncio.create_task(wait_for_payment(payment_id, cb))


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
    dp.register_callback_query_handler(
        confirm_payment_irbis,
        lambda c: c.data == "confirm_irbis_payment",
        state="*",
    )
