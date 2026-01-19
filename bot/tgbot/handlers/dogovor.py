from aiogram import Dispatcher
from aiogram.types import CallbackQuery, InputFile

from bot.tgbot.keyboards.inline import *
from bot.tgbot.databases.pay_db import *



async def dogovor_inline(cb: CallbackQuery):
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
        username = cb.from_user.username
        if username == None:
            await cb.message.edit_text('''
    Для корректной работы необходимо в настройках изменить имя пользователя!
    Как это сделать:
    Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
    После изменения @username войдите в бот по ссылке еще раз и нажмите /start
    ''')
        else:
            await cb.message.edit_text('<b>https://telegra.ph/Dogovor-s-DOMOS-12-08</b>', reply_markup=mainmenu_mk)


def register_dogovor(dp: Dispatcher):
    dp.register_callback_query_handler(dogovor_inline, lambda c: c.data == 'dogovor', state='*')


