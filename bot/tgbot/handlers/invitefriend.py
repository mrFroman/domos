from aiogram import Dispatcher
from aiogram.types import CallbackQuery

from bot.tgbot.keyboards.inline import *
from bot.tgbot.databases.pay_db import *


async def invite_inline(cb: CallbackQuery):
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
                msg = f'''
<b>Хочется получить бесплатный месяц? Не проблема — просто пригласите коллег.</b>

Пришлите им приглашение с индивидуальной реферальной ссылкой. Для этого нужно отправить вашу ссылку другу, бот отправил вам ее вторым сообщением

<i>Как только приглашенный вами друг оплатит месяц договора вы получите месяц бесплатно</i>'''
                await cb.message.edit_text(msg, reply_markup=mainmenu_mk)
                await cb.message.answer(f'https://t.me/DomosproBot?start={cb.from_user.id}')
        else:
            await cb.answer('⭕ Сначала оплатите подписку!', show_alert=True)


def register_invite(dp: Dispatcher):
    dp.register_callback_query_handler(
        invite_inline, lambda c: c.data == 'invite_friend', state='*')
