from aiogram import Dispatcher
from aiogram.types import CallbackQuery, InputFile

from bot.tgbot.keyboards.inline import *
from bot.tgbot.databases.pay_db import *


async def needed_inline(cb: CallbackQuery):
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
        payed = getUserPay(cb.from_user.id)
        if payed == 1:
            username = cb.from_user.username
            if username == None:
                await cb.message.edit_text('''
        Для корректной работы необходимо в настройках изменить имя пользователя!
        Как это сделать:
        Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
        После изменения @username войдите в бот по ссылке еще раз и нажмите /start
        ''')
            else:
                await cb.message.edit_text('<b>Доступы</b>', reply_markup=neededaccess_mk)
        else:
            await cb.answer('⭕ Сначала оплатите подписку!', show_alert=True)


async def neededcrm_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>https://telegra.ph/CRM-12-28</b>', reply_markup=mainmenu_mk)


async def neededdomclick_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>https://telegra.ph/Domklik-12-28</b>', reply_markup=mainmenu_mk)


async def neededupn_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>https://telegra.ph/UPN-12-28</b>', reply_markup=mainmenu_mk)


async def needednmarket_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>https://telegra.ph/Nmarket-12-28</b>', reply_markup=mainmenu_mk)


async def neededavito_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>https://telegra.ph/Avito-12-28</b>', reply_markup=mainmenu_mk)


def register_needed(dp: Dispatcher):
    dp.register_callback_query_handler(
        needed_inline, lambda c: c.data == 'needed', state='*')
    dp.register_callback_query_handler(
        neededcrm_inline, lambda c: c.data == 'crm', state='*')
    dp.register_callback_query_handler(
        neededdomclick_inline, lambda c: c.data == 'domclick', state='*')
    dp.register_callback_query_handler(
        neededupn_inline, lambda c: c.data == 'upn', state='*')
    dp.register_callback_query_handler(
        needednmarket_inline, lambda c: c.data == 'nmarket', state='*')
    dp.register_callback_query_handler(
        neededavito_inline, lambda c: c.data == 'avito', state='*')
