import uuid
import os
from datetime import datetime
from typing import Union

from aiogram import Dispatcher
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import MessageNotModified
from bot.tgbot.databases.pay_db import (
    createPayment,
    createRecurrentPayment,
    get_rec_payment,
    getUserEndPay,
    getUserPay,
    update_user_full_name,
)
from bot.tgbot.handlers.tinkoff_api import TinkoffPayment
from bot.tgbot.keyboards.inline import (
    genPaymentMk,
    month_subscription_services_kb,
    payment_mk,
    mainmenubackbtnmk,
)
from bot.tgbot.misc.states import createDepositState
from bot.tgbot.databases.database import AsyncDatabaseConnection, DB_TYPE
from config import BASE_DIR, MAIN_DB_PATH, logger_bot
from bot.tgbot.databases.database import DatabaseConnection
from dotenv import load_dotenv, find_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv(find_dotenv())




MONTH_SUBSCRIPTION_TEXT = """
💎 <b>Ежемесячная подписка Domos Club</b>

В подписку входит:

🏢 <b>Офис 24/7</b>  
• Полностью оборудованный офис  
• Переговорные комнаты  
• Кофе, чай, фрукты  

🤖 <b>Чат-бот Domos</b>  
• Календарь мероприятий  
• Бронирование переговорок  
• Документы и шаблоны  
• Проверка объектов  
• Оплата подписки  
• Автодоговоры и ИИ  
• Ипотека и оценка объектов  
• Новостройки и презентации  
• Контент и сценарии для соцсетей  

⚖️ <b>Юрист</b>  
• Консультации агентов  
• Составление договоров  
• Проверка объектов  

💰 <b>Налоговый консультант</b>  
• Консультации по налогообложению  

👩‍💼 <b>Офис-менеджер</b>  
• Рекламные пакеты  
• Регистрация авансов  
• Агентские договоры  

📊 <b>CRM и сопровождение объектов</b>  
• Заведение объектов  
• Контроль ошибок на агрегаторах  

🎉 <b>Мероприятия</b>  
• Domos Club  
• Бизнес-игры  

🧠 <b>Психолог</b>  
• Личные консультации  
• Бизнес-игры  
• Тренинги  

🎓 <b>Обучение и презентации</b>  
• Онлайн-трансляции  
• Записи в отдельном канале  

📸 <b>Фотосессия</b>  
• 1 фотосессия  
• 10 профессиональных фото  

⏳ <b>Проекты развития</b>  
• «12 недель»  
• «Магия утра»  

🎊 <b>Корпоративы</b>  
• Праздники  
• Походы и сплавы  
• Спортивные мероприятия  

📚 <b>Шпаргалка риелтора</b>  
• Акции застройщиков  
• Старты продаж  
• Контент для соцсетей  
• Брокер-туры  
• Повышенные вознаграждения  

"""

def create_payment1(price, desc, fullname):
    user_id = fullname
    order_id = str(uuid.uuid4())  # уникальный ID заказа
    amount = price  # сумма платежа в рублях
    description = desc

    payment_data = TinkoffPayment.init_payment(
        amount=amount,
        order_id=order_id,
        description=description,
        customer_key=str(user_id),
    )

    if payment_data.get("Success", False):
        payment_url = payment_data["PaymentURL"]
        payment_id = payment_data["PaymentId"]
        return payment_id, payment_url
    else:
        logger_bot.error("Ошибка при создании платежа. Попробуйте позже.")


def create_recurrent_payment(price, desc, user_id):
    order_id = str(uuid.uuid4())  # уникальный ID заказа
    amount = price  # сумма платежа в рублях
    description = desc

    payment_data = TinkoffPayment.initial_recurrent_payment(
        amount=amount,
        order_id=order_id,
        description=description,
        customer_key=str(user_id),
    )

    if payment_data.get("Success", False):
        payment_id = payment_data["PaymentId"]
        payment_url = payment_data["PaymentURL"]
        logger_bot.info(
            f"Создан платёж в Tinkoff API с payment_id: {payment_id} и payment_url: {payment_url}",
        )
        # Создаем запись о рекуррентном платеже в БД
        createRecurrentPayment(payment_id, amount, user_id)

        return payment_id, payment_url
    else:
        logger_bot.error("Ошибка при создании платежа. Попробуйте позже.")


# temp_msg = """<b>Раздел недоступен. Оплату за апрель необходимо провести на карту Альфа банка по номеру Владимира Лебедева 89634450770)
# И отправить квитанцию Ирине Гурдуза в WhatsApp <a href="https://wa.me/79193747077">+7 919 374-70-77</a></b>"""

FORCED_USER_ID = "1094432705"

from aiogram import types
NEXT_PAYMENT_DATE  = datetime(2025, 2, 28, tzinfo=timezone.utc)


async def sub_pay_active_mes(message: types.Message):
    today = datetime.now(timezone.utc).date()
    result_lines = []

    db = AsyncDatabaseConnection(MAIN_DB_PATH, schema="main")
    
    # Получаем активные подписки
    query = """
        SELECT id, user_id, start_pay_date, end_pay_date
        FROM rec_payments
        WHERE status = 'active'
           OR user_id = %s
    """
    payments = await db.fetchall(query, (FORCED_USER_ID,))

    if not payments:
        await message.answer("❌ Активных подписок не найдено")
        return

    for payment in payments:
        if isinstance(payment, dict):
            payment_id = payment.get('id')
            user_id = payment.get('user_id')
            start_date = payment.get('start_pay_date')
            end_date = payment.get('end_pay_date')
        else:
            payment_id = payment[0]
            user_id = payment[1]
            start_date = payment[2]
            end_date = payment[3]
        
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        fixed = False

        # Если подписка создана сегодня — дата следующей оплаты = 28.02.2026
        if start_dt.date() == today:
            fixed_end = NEXT_PAYMENT_DATE
            fixed = True
        else:
            fixed_end = end_dt

        start_ts = int(start_dt.timestamp())  # сегодня
        end_ts = int(fixed_end.timestamp())   # следующая оплата

        # Адаптируем SQL для разных БД
        if DB_TYPE == "postgres":
            # обновляем rec_payments — только end_pay_date
            await db.execute(
                """
                UPDATE rec_payments
                SET end_pay_date = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (fixed_end.isoformat(), payment_id),
            )

            # обновляем users
            await db.execute(
                """
                UPDATE users
                SET pay_status = 1,
                    last_pay = %s,
                    end_pay = %s
                WHERE user_id = %s
                """,
                (start_ts, end_ts, user_id),
            )
        else:
            # обновляем rec_payments — только end_pay_date
            await db.execute(
                """
                UPDATE rec_payments
                SET end_pay_date = %s,
                    updated_at = datetime('now')
                WHERE id = %s
                """,
                (fixed_end.isoformat(), payment_id),
            )

            # обновляем users
            await db.execute(
                """
                UPDATE users
                SET pay_status = 1,
                    last_pay = %s,
                    end_pay = %s
                WHERE user_id = %s
                """,
                (start_ts, end_ts, user_id),
            )

        mark = "🛠" if fixed else "✅"
        result_lines.append(
            f"{mark} user_id={user_id} | payment_id={payment_id}"
        )

    # Telegram ограничение ~4096 символов
    text = "Активированные пользователи:\n\n" + "\n".join(result_lines)
    if len(text) > 3900:
        text = f"Активировано пользователей: {len(result_lines)}\n⚠️ Список слишком большой, смотри логи"

    await message.answer(text)


async def sub_pay_active(update: Union[Message, CallbackQuery], state: FSMContext):
    if isinstance(update, CallbackQuery):
        message = update.message
        user = update.from_user
        reply = message.edit_text
    else:
        message = update
        user = update.from_user
        reply = message.answer 

    user_data = await state.get_data()
    fullname = user_data.get("fullname")

    username = user.username
    user_id = user.id

    if username is None:
        await reply(
            """
                Для корректной работы необходимо в настройках изменить имя пользователя!
                Как это сделать:
                Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
                После изменения @username войдите в бот по ссылке еще раз и нажмите /start
                """
        )
        return

    _, payment_url = create_recurrent_payment(
        price=int(os.getenv("MOUNTH_SUBSCRIPTION_PRICE", 10000)),
        desc=f"Оплата подписки от\n ФИО: {fullname}",
        user_id=user_id,
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    "🔁 Подключить подписку",
                    url=payment_url,
                )
            ]
        ]
    )

    await reply(
        f"Сумма: 12000 рублей.\n"
        "Период списания: 1 раз в месяц.\n"
        "Время на оплату: 30 минут.\n\n"
        "Списания будут происходить автоматически.\n"
        "После оплаты кнопка «🔁 Подключить подписку»\n"
        "сменится на «❌ Отключить подписку»\n\n"
        "По вопросам о подписке обращаться на почту lebedev@domos.club\n",
        reply_markup=keyboard,
    )



# async def sub_pay_active(update: Union[Message, CallbackQuery]):
#     if isinstance(update, CallbackQuery):
#         user = update.from_user
#         send = update.message.answer
#         await update.answer()
#     else:
#         user = update.from_user
#         send = update.answer

#     username = user.username
#     user_id = user.id

#     if username is None:
#         await send(
#             """
#             Для корректной работы необходимо в настройках изменить имя пользователя!
#             Как это сделать:
#             Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
#             После изменения @username войдите в бот по ссылке еще раз и нажмите /start
#             """
#         )
#         return

#     _, payment_url = create_recurrent_payment(
#         price=int(os.getenv("MOUNTH_SUBSCRIPTION_PRICE", 10000)),
#         desc="Оплата подписки",
#         user_id=user_id,
#     )

#     keyboard = InlineKeyboardMarkup(
#         inline_keyboard=[
#             [
#                 InlineKeyboardButton(
#                     "🔁 Подключить подписку",
#                     url=payment_url,
#                 )
#             ]
#         ]
#     )

#     await send(
#         "💳 <b>Подписка на месяц</b>\n\n"
#         "Сумма: 10 000 рублей\n"
#         "Период списания: 1 раз в месяц\n"
#         "Время на оплату: 30 минут\n\n"
#         "Списания будут происходить автоматически.\n"
#         "После оплаты кнопка сменится на «❌ Отключить подписку»\n\n"
#         "По вопросам: lebedev@domos.club",
#         reply_markup=keyboard,
#     )

# async def sub_pay_cancel(update: Union[Message, CallbackQuery]):
#     if isinstance(update, CallbackQuery):
#         user = update.from_user
#         send = update.message.answer
#     else:
#         user = update.from_user
#         send = update.answer

#     username = user.username
#     user_id = user.id

#     if username is None:
#         await send(
#             """
#             Для корректной работы необходимо в настройках изменить имя пользователя!
#             Как это сделать:
#             Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
#             После изменения @username войдите в бот по ссылке еще раз и нажмите /start
#             """
#         )
#         return

#     rec_payment = get_rec_payment(user_id)
#     end_date_raw = rec_payment[0][9]
#     end_date_dt = datetime.fromisoformat(end_date_raw)
#     end_date = end_date_dt.strftime("%d/%m/%Y %H:%M")

#     keyboard = InlineKeyboardMarkup(
#         inline_keyboard=[
#             [
#                 InlineKeyboardButton(
#                     "❌ Отключить подписку",
#                     callback_data="sub_pay_cancel_confirm",
#                 )
#             ]
#         ]
#     )

#     await send(
#         f"Ваша подписка активна.\n"
#         f"Действует до: {end_date}\n\n",
#         reply_markup=keyboard,
#     )

async def sub_pay_cancel(update: Union[Message, CallbackQuery]):
    """
    Показывает информацию о текущей подписке и кнопку «Отключить подписку».
    Работает как по команде /sub_cancel, так и по нажатию инлайн-кнопки.
    """
    if isinstance(update, CallbackQuery):
        await update.answer()
        user = update.from_user
        reply = update.message.edit_text
    else:
        user = update.from_user
        reply = update.answer

    username = user.username
    user_id = user.id

    if username is None:
        await reply(
            """
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
"""
        )
        return

    rec_payment = get_rec_payment(user_id)
    end_date = None

    if rec_payment:
        row = rec_payment[0]
        if isinstance(row, dict):
            end_date_raw = row.get("end_pay_date") or row.get("END_PAY_DATE")
        else:
            end_date_raw = row[9] if len(row) > 9 else None
        if end_date_raw:
            end_date_dt = datetime.fromisoformat(str(end_date_raw))
            end_date = end_date_dt.strftime("%d/%m/%Y %H:%M")

    if not end_date and getUserPay(user_id) == 1:
        # Подписка активна по users (разовый платёж или старая запись), дата из users.end_pay
        end_ts = getUserEndPay(user_id)
        if end_ts:
            end_date_dt = datetime.fromtimestamp(end_ts)
            end_date = end_date_dt.strftime("%d/%m/%Y %H:%M")

    if not end_date:
        await reply("У вас нет активной подписки.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    "❌ Отключить подписку",
                    callback_data="sub_pay_cancel_confirm",
                )
            ]
        ]
    )

    await reply(
        f"Ваша подписка активна.\n"
        f"Действует до: {end_date}.\n\n",
        reply_markup=keyboard,
    )


async def payment_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username is None:
        await cb.message.edit_text(
            """
            Для корректной работы необходимо в настройках изменить имя пользователя!
            Как это сделать:
            Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
            После изменения @username войдите в бот по ссылке еще раз и нажмите /start
            """
        )
    else:
        now_pay = getUserPay(cb.from_user.id)
        if now_pay != 1:
            await cb.message.edit_text(
                "<b>Выберите период оплаты:</b>",
                reply_markup=payment_mk,
            )
        else:
            end = datetime.fromtimestamp(getUserEndPay(cb.from_user.id))
            await cb.message.edit_text(
                f"<b>Дата окончания подписки: {end}</b>\n"
                + "<b>Выберите период оплаты:</b>",
                reply_markup=payment_mk,
                disable_web_page_preview=True,
            )


async def sub_pay_cancel_confirm_handler(cb: CallbackQuery):
    """
    Обработчик нажатия на кнопку «❌ Отключить подписку».
    Отключает подписку пользователя и помечает рекуррентные платежи как отменённые.
    """
    await cb.answer()
    username = cb.from_user.username
    user_id = cb.from_user.id

    if username is None:
        await cb.message.edit_text(
            """
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
"""
        )
        return

    try:
        # Не трогаем users — доступ остаётся до конца оплаченного периода.
        # Только отключаем рекуррентные списания (автопродление).
        db = DatabaseConnection(MAIN_DB_PATH, schema="main")
        db.execute(
            """
            UPDATE rec_payments
            SET status = %s
            WHERE user_id = %s AND status = %s
            """,
            ("cancelled", user_id, "active"),
        )

        await cb.message.edit_text(
            "Автоматические списания отключены. Доступ по подписке сохранится до конца оплаченного периода."
        )
    except Exception as e:
        logger_bot.exception("Ошибка при отключении подписки: %s", e)
        await cb.message.edit_text(
            "Не удалось отключить подписку. Попробуйте позже или напишите в поддержку: lebedev@domos.club"
        )



async def choseddep_inline(cb: CallbackQuery, state: FSMContext):
    username = cb.from_user.username
    if username is None:
        await cb.message.edit_text(
            """
            Для корректной работы необходимо в настройках изменить имя пользователя!
            Как это сделать:
            Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
            После изменения @username войдите в бот по ссылке еще раз и нажмите /start
            """
        )
        return

    chosed = cb.data.split("_")[1]

    # ✅ МЕСЯЦ → РЕКУРРЕНТНАЯ ПОДПИСКА
    # if chosed == "month":
    #     await sub_pay_active(cb)
    #     return
    if chosed == "month":
        await state.update_data(payment_type="recurrent")
        await cb.message.edit_text(
            "Введите ваше ФИО (обязательно проверьте данные перед отправкой)\n\n"
            "Пример: <code>Иванов Иван Иванович</code>",
            reply_markup=mainmenubackbtnmk,
        )
        await state.set_state(createDepositState.fullname)
        return

    # ⬇️ всё остальное — разовые платежи
    price_map = {
        "open": 13700,
        "three": 30000,
        "halfyear": 60000,
        "year": 120000,
    }

    price = price_map.get(chosed)
    if not price:
        await cb.answer("Неизвестный тип оплаты")
        return

    await state.update_data(price=price)
    await cb.message.edit_text(
        "Введите ваше ФИО (обязательно проверьте данные перед отправкой)\n\n"
        "Пример: <code>Иванов Иван Иванович</code>",
        reply_markup=mainmenubackbtnmk,
    )
    await state.set_state(createDepositState.fullname.state)

# async def choseddep_inline(cb: CallbackQuery, state: FSMContext):
#     username = cb.from_user.username
#     if username is None:
#         await cb.message.edit_text(
#             """
# Для корректной работы необходимо в настройках изменить имя пользователя!
# Как это сделать:
# Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
# После изменения @username войдите в бот по ссылке еще раз и нажмите /start
# """
#         )
#     else:
#         price = 0
#         chosed = cb.data.split("_")[1]
#         if chosed == "month":
#             price = 10000
#         elif chosed == "open":
#             price = 13070
#         elif chosed == "three":
#             price = 30000
#         elif chosed == "halfyear":
#             price = 60000
#         elif chosed == "year":
#             price = 120000
#         # TODO Скрыть тест при загрузке на сервер
#         # elif chosed == "test":
#         #     price = 1
#         await state.update_data(price=price)
#         await cb.message.edit_text(
#             "Введите ваше ФИО (обязательно проверьте данные перед отправкой)\n\nПример: <code>Иванов Иван Иванович</code>",
#             reply_markup=mainmenubackbtnmk,
#         )
#         await state.set_state(createDepositState.fullname.state)


async def fullnameChoicedDep(message: Message, state: FSMContext):
    await state.update_data(fullname=message.text)
    user_data = await state.get_data()
    payment_type = user_data.get("payment_type")

    update_user_full_name(message.from_user.id, message.text)

    # --- РЕКУРРЕНТ ---
    if payment_type == "recurrent":
        await sub_pay_active(message, state)
        return

    
    price = user_data["price"]

    payment_id, payment_link = create_payment1(
        price,
        "Покупка подписки",
        message.text,
    )

    createPayment(payment_id, price, message.from_user.id)
    caption = f"Сумма: {price} RUB\n"
    "Время на оплату: 30 минут\n\n"
    "Оплата:"

    with open(
        os.path.join(BASE_DIR, "bot", "tgbot", "Оферта_ЦН_Домос.docx"), "rb"
    ) as doc_file:
        await message.answer_document(
            doc_file,
            caption=caption,
            reply_markup=genPaymentMk(payment_id, payment_link),
        )
    await state.finish()


async def month_one_time(cb: CallbackQuery, state: FSMContext):
    price = 12000

    await state.set_state(createDepositState.price.state)
    await state.update_data(price=price)
    await state.set_state(createDepositState.fullname.state)

    await cb.message.edit_text(
        'Введите ваше ФИО (обязательно проверьте данные перед отправкой)\n\n'
        'Пример: <code>Иванов Иван Иванович</code>',
        reply_markup=mainmenubackbtnmk
    )


async def month_recurrent(cb: CallbackQuery):
    if cb.message.text == MONTH_SUBSCRIPTION_TEXT:
        await cb.answer()
        return

    try:
        await cb.message.edit_text(
            MONTH_SUBSCRIPTION_TEXT,
            reply_markup=month_subscription_services_kb(),
            disable_web_page_preview=True,
        )
    except MessageNotModified:
        await cb.answer()



# def register_payment(dp: Dispatcher):
#     dp.register_callback_query_handler(
#         payment_inline,
#         lambda c: c.data == "pay_invoice",
#         state="*"
#     )

#     dp.register_callback_query_handler(
#         sub_pay_active,
#         lambda c: c.data == "sub_active",
#         state="*",
#     )

#     dp.register_callback_query_handler(
#         sub_pay_cancel,
#         lambda c: c.data == "sub_pay_cancel",
#         state="*",
#     )

#     dp.register_callback_query_handler(
#         choseddep_inline,
#         lambda c: c.data.startswith("buysub_"),
#         state="*"
#     )

#     dp.register_callback_query_handler(
#         month_one_time,
#         lambda c: c.data == "month_one_time",
#         state="*"
#     )

#     dp.register_callback_query_handler(
#         month_recurrent,
#         lambda c: c.data == "month_recurrent",
#         state="*"
#     )

#     dp.register_message_handler(
#         fullnameChoicedDep,
#         state=createDepositState.fullname
#     )

def register_payment(dp: Dispatcher):
    dp.register_callback_query_handler(
        payment_inline, lambda c: c.data == "pay_invoice", state="*"
    )
    # TODO Изменить обработчик при выгрузке на сервер
    # dp.register_callback_query_handler(
    #     sub_pay_active, lambda c: c.data == "sub_pay_active", state="*"
    # )
    dp.register_callback_query_handler(
        sub_pay_cancel, lambda c: c.data == "sub_pay_cancel", state="*"
    )

    dp.register_callback_query_handler(
        month_recurrent, lambda c: c.data == "sub_advantages", state="*"
    )

    dp.register_message_handler(
        sub_pay_active,
        commands="sub_active",
        state="*",
    )
    dp.register_message_handler(
        sub_pay_cancel,
        commands="sub_cancel",
        state="*",
    )

    dp.register_message_handler(
        sub_pay_active_mes,
        commands="sub_mes",
        state="*",
    )

    dp.register_callback_query_handler(
        choseddep_inline, lambda c: "buysub_" in c.data, state="*"
    )
    dp.register_callback_query_handler(
        sub_pay_cancel_confirm_handler,
        lambda c: c.data == "sub_pay_cancel_confirm",
        state="*",
    )
    dp.register_message_handler(fullnameChoicedDep, state=createDepositState.fullname)
