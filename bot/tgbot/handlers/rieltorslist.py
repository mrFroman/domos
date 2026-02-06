from aiogram import Dispatcher
from aiogram.types import CallbackQuery

from bot.tgbot.keyboards.inline import *
from bot.tgbot.databases.pay_db import *


async def rieltors_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        page = 1  # По умолчанию начинаем с первой страницы
        keyboard = genRieltorsList(page)
        await cb.message.edit_text('<b>Выберите риэлтора:</b>', reply_markup=keyboard)

async def showrieltor_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if not username:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
        return

    rieltor_id = cb.data.split('_')[1]
    rieltor = getRieltorId(rieltor_id)

    name = rieltor.get("full_name", "Без имени")
    email = rieltor.get("email", "Без email")
    photo = rieltor.get("photo")  # это file_id от Telegram
    phone = rieltor.get("phone", "Без телефона")

    msg = f'''
        <code>🧿 ФИО:</code> {name}         
        <code>📱 Телефон:</code> {phone}     
        <code>📩 E-mail:</code> {email}             
        '''

    try:
        # Попытка отправить фото
        if photo:
            await cb.message.answer_photo(photo, msg, reply_markup=GenRieltorShowMK(cb.from_user.id, rieltor_id))
        else:
            raise ValueError("Фото отсутствует")
    except Exception as e:
        # Если ошибка (например WrongFileIdentifier) → просто текст
        logger_bot.warning(f"Фото риелтора {rieltor_id} не отправлено: {e}")
        await cb.message.answer(msg, reply_markup=GenRieltorShowMK(cb.from_user.id, rieltor_id))


async def delrieltor_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        rieltor_id = cb.data.split('_')[1]
        delRietlor(rieltor_id)
        msg = f'''<code>🧿 Риелтор успешно удален:</code>'''
        await cb.message.answer(msg, reply_markup=rieltorsbackbtnmk)

async def rieltors_answer(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.answer('<b>Выберите риэлтора:</b>', reply_markup=genRieltorsList(1))

# Обработка колбэков
async def callback_edit_page(cb: CallbackQuery):
    new_page = int(cb.data.split('_')[2])
    #print('New page - ', new_page)
    keyboard = genRieltorsList(new_page)
    await cb.message.edit_reply_markup(reply_markup=keyboard)




def register_rieltorslist(dp: Dispatcher):
    dp.register_callback_query_handler(rieltors_inline, lambda c: c.data == 'helpfulrieltorslist', state='*')
    dp.register_callback_query_handler(rieltors_answer, lambda c: c.data == 'helpfulrieltorslistanswer', state='*')
    dp.register_callback_query_handler(showrieltor_inline, lambda c: 'showrieltor_' in c.data, state='*')
    dp.register_callback_query_handler(delrieltor_inline, lambda c: 'delrietl_' in c.data, state='*')
    dp.register_callback_query_handler(callback_edit_page, lambda c: 'rieltors_page_' in c.data, state='*' )
