from aiogram import Dispatcher, types
from aiogram.types import CallbackQuery, Message
from bot.tgbot.handlers.payment import sub_pay_active
from tgbot.keyboards.inline import *
from tgbot.databases.pay_db import *
from aiogram.dispatcher import FSMContext
from tgbot.misc.states import *
import uuid
from tgbot.handlers.tinkoff_api import TinkoffPayment
path = str(Path(__file__).parents[2])



def create_payment1(price, desc, fullname):
    user_id = fullname
    order_id = str(uuid.uuid4())  # уникальный ID заказа
    amount = price  # сумма платежа в рублях
    description = desc
    
    # Инициализация платежа
    payment_data = TinkoffPayment.init_payment(
        amount=amount,
        order_id=order_id,
        description=description,
        customer_key=str(user_id)
    )
    
    print(payment_data)
    
    if payment_data.get('Success', False):
        payment_url = payment_data['PaymentURL']
        payment_id = payment_data['PaymentId']
        return payment_id, payment_url
        # Отправляем пользователю кнопку для оплаты
        #await message.reply(
            #f"Сумма к оплате: {amount} руб.\n"
           # f"Описание: {description}",
          #  reply_markup=get_payment_keyboard(payment_url, payment_id)
       # )
    else:
        #await message.reply("Ошибка при создании платежа. Попробуйте позже.")
        print("Ошибка при создании платежа. Попробуйте позже.")

    



temp_msg = '''<b>Раздел недоступен. Оплату за апрель необходимо провести на карту Альфа банка по номеру Владимира Лебедева 89634450770)
И отправить квитанцию Ирине Гурдуза в WhatsApp <a href="https://wa.me/79193747077">+7 919 374-70-77</a></b>'''

async def payment_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        now_pay = getUserPay(cb.from_user.id)
        if now_pay != 1:
            await cb.message.edit_text('<b>Выберите период оплаты:</b>', reply_markup=payment_mk)
            #await cb.message.edit_text(temp_msg, reply_markup=mainmenubackbtnmk, disable_web_page_preview=True)
        else:
            end = datetime.datetime.fromtimestamp(getUserEndPay(cb.from_user.id))
            #await cb.message.edit_text(f'<b>Дата окончания подписки: {end}</b>\n' + temp_msg, reply_markup=mainmenubackbtnmk, disable_web_page_preview=True)
            await cb.message.edit_text(f'<b>Дата окончания подписки: {end}</b>\n' + '<b>Выберите период оплаты:</b>', reply_markup=payment_mk, disable_web_page_preview=True)




async def choseddep_inline(cb: CallbackQuery, state: FSMContext):
    username = cb.from_user.username
    if username is None:
        await cb.message.edit_text(
            '''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
'''
        )
        return

    chosed = cb.data.split('_')[1]

    # ✅ МЕСЯЦ — СПРОСИТЬ СПОСОБ ОПЛАТЫ
    if chosed == 'month':
        await cb.message.edit_text(
            "Выберите способ оплаты подписки на месяц:",
            reply_markup=chooseMonthPaymentMk()
        )
        return

    # ⬇️ ВСЁ ОСТАЛЬНОЕ — СТАРАЯ ЛОГИКА
    price_map = {
        "open": 11610,
        "three": 30000,
        "halfyear": 60000,
        "year": 108000,
    }

    price = price_map.get(chosed)
    if not price:
        return

    await state.set_state(createDepositState.price.state)
    await state.update_data(price=price)
    await state.set_state(createDepositState.fullname.state)

    await cb.message.edit_text(
        'Введите ваше ФИО (обязательно проверьте данные перед отправкой)\n\n'
        'Пример: <code>Иванов Иван Иванович</code>',
        reply_markup=mainmenubackbtnmk
    )

# async def choseddep_inline(cb: CallbackQuery, state: FSMContext):
#     username = cb.from_user.username
#     if username == None:
#         await cb.message.edit_text('''
# Для корректной работы необходимо в настройках изменить имя пользователя!
# Как это сделать:
# Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
# После изменения @username войдите в бот по ссылке еще раз и нажмите /start
# ''')
#     else:
#         price = 0
#         chosed = cb.data.split('_')[1]
#         if chosed == 'month':
#             price = 10000
#         elif chosed == 'open':
#             # price = 12897
#             price = 11610
#         elif chosed == 'three':
#             price = 30000
#         elif chosed == 'halfyear':
#             price = 60000
#         elif chosed == 'year':
#             price = 108000
#         # await state.set_state(createDepositState.payment_id.state)
#         # await state.update_data(payment_id=payment_id)
#         # await state.set_state(createDepositState.payment_link.state)
#         # await state.update_data(payment_link=payment_link)
#         await state.set_state(createDepositState.price.state)
#         await state.update_data(price=price)
#         await state.set_state(createDepositState.fullname.state)
#         await cb.message.edit_text('Введите ваше ФИО (обязательно проверьте данные перед отправкой)\n\nПример: <code>Иванов Иван Иванович</code>', reply_markup=mainmenubackbtnmk)


async def fullnameChoicedDep(message: Message, state: FSMContext):

    await state.update_data(fullname=message.text)
    print(message.text)
    user_data = await state.get_data()
    price = user_data['price']
    print(1123)
    payment_id, payment_link = create_payment1(price, 'Покупка подписки', message.text)
    update_user_full_name(message.from_user.id, message.text)
    createPayment(payment_id, price, message.from_user.id)
    print(3)
    caption = (
        f'Сумма: {price} RUB\n'
        f'Время на оплату: 30 минут\n\n'
        'Оплата:'
    )

    with open(f'{path}/tgbot/Оферта_ЦН_Домос.docx', 'rb') as doc_file:
        await message.answer_document(
            doc_file,
            caption=caption,
            reply_markup=genPaymentMk(payment_id, payment_link)
        )
    await state.finish()



async def month_one_time(cb: CallbackQuery, state: FSMContext):
    price = 10000

    await state.set_state(createDepositState.price.state)
    await state.update_data(price=price)
    await state.set_state(createDepositState.fullname.state)

    await cb.message.edit_text(
        'Введите ваше ФИО (обязательно проверьте данные перед отправкой)\n\n'
        'Пример: <code>Иванов Иван Иванович</code>',
        reply_markup=mainmenubackbtnmk
    )



async def month_recurrent(cb: CallbackQuery):
    await sub_pay_active(cb)



def register_payment(dp: Dispatcher):
    dp.register_callback_query_handler(payment_inline, lambda c: c.data == 'pay_invoice', state='*')
    dp.register_callback_query_handler(choseddep_inline, lambda c: 'buysub_' in c.data, state='*')
    dp.register_message_handler(fullnameChoicedDep, state=createDepositState.fullname)
    dp.register_callback_query_handler(
        month_one_time,
        lambda c: c.data == "month_one_time",
        state="*"
    )

    dp.register_callback_query_handler(
        month_recurrent,
        lambda c: c.data == "month_recurrent",
        state="*"
    )
