from aiogram import Dispatcher
from aiogram.types import CallbackQuery

from bot.tgbot.keyboards.inline import *
from bot.tgbot.databases.pay_db import *


async def whatsup_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>После добавления в группу обязательно ознакомьтесь с описанием чата!</b>', reply_markup=whatsup_mk)



def register_whatsup(dp: Dispatcher):
    dp.register_callback_query_handler(whatsup_inline, lambda c: c.data == 'whtschats', state='*')
