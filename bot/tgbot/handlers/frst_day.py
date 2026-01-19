from aiogram import Dispatcher
from aiogram.types import CallbackQuery

from bot.tgbot.keyboards.inline import *
from bot.tgbot.databases.pay_db import *


async def first_day_inline(cb: CallbackQuery):
    print('sss')
    payed = getUserPay(cb.from_user.id)
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
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
                await cb.message.edit_text('<b>Любой текст по желанию</b>', reply_markup=frstday_mk)
        else:
            await cb.answer('⭕ Сначала оплатите подписку!', show_alert=True)



def register_frstday(dp: Dispatcher):
    dp.register_callback_query_handler(first_day_inline, lambda c: c.data == 'fst_day', state='*')
