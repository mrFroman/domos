from aiogram import Dispatcher
from aiogram.types import CallbackQuery

from bot.tgbot.keyboards.inline import *
from bot.tgbot.databases.pay_db import *


async def contacts_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>Выберите контакт:</b>', reply_markup=genRieltorsList())


async def showcontact_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        contact_id = cb.data.split('_')[1]
        contact = getContactId(contact_id)
        name = contact[1]
        email = contact[2]
        photo = contact[3]
        phone = contact[4]
        job = contact[5]
        msg = f'''
<code>🧿 ФИО:</code> {name}
<code>👨‍💼 Должность:</code> {job}         
<code>📱 Телефон:</code> {phone}     
<code>📩 E-mail:</code> {email}'''
        await cb.message.answer_photo(photo, msg, reply_markup=GenContactShowMK(cb.from_user.id, contact_id))


async def delcontact_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        contact_id = cb.data.split('_')[1]
        delContact(contact_id)
        msg = f'''<code>🧿 Контакт успешно удален:</code>'''
        await cb.message.answer(msg, reply_markup=contactsbacanswerkbtn)


async def contacts_answer(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.answer('<b>Выберите контакт:</b>', reply_markup=genContactsList())


def register_contacts(dp: Dispatcher):
    dp.register_callback_query_handler(
        contacts_inline, lambda c: c.data == 'contacntshelpful', state='*')
    dp.register_callback_query_handler(
        contacts_answer, lambda c: c.data == 'contacntshelpfulanswer', state='*')
    dp.register_callback_query_handler(
        showcontact_inline, lambda c: 'showcontacts_' in c.data, state='*')
    dp.register_callback_query_handler(
        delcontact_inline, lambda c: 'delcont_' in c.data, state='*')
