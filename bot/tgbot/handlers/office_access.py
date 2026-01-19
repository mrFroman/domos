from aiogram import Dispatcher
from aiogram.types import CallbackQuery

from bot.tgbot.keyboards.inline import *
from bot.tgbot.databases.pay_db import *


async def office_access_inline(cb: CallbackQuery):
    username = cb.from_user.username
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
        if username == None:
            await cb.message.edit_text('''
    Для корректной работы необходимо в настройках изменить имя пользователя!
    Как это сделать:
    Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
    После изменения @username войдите в бот по ссылке еще раз и нажмите /start
    ''')
        else:
            await cb.message.edit_text('<b>https://telegra.ph/Dostup-v-ofis-12-07</b>', reply_markup=mainmenu_mk)



def register_office_access(dp: Dispatcher):
    dp.register_callback_query_handler(office_access_inline, lambda c: c.data == 'office_access', state='*')
