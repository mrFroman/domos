from aiogram import Dispatcher
from aiogram.types import CallbackQuery, InputFile

from bot.tgbot.keyboards.inline import *
from bot.tgbot.databases.pay_db import *



async def rules_inline(cb: CallbackQuery):
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
                await cb.message.edit_text('<b>Правила:</b>', reply_markup=rules_mk)

        else:
            await cb.answer('⭕ Сначала оплатите подписку!', show_alert=True)

async def officeManager_inline(cb: CallbackQuery):
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
               await cb.message.edit_text('<b>https://telegra.ph/Ofis-menedzher-12-08-6</b>', reply_markup=ourrulesbackbtnmk)
        else:
            await cb.answer('⭕ Сначала оплатите подписку!', show_alert=True)



async def loer_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>https://telegra.ph/YUrist-12-08</b>', reply_markup=ourrulesbackbtnmk)

async def goodday_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>https://telegra.ph/Bi-heppi-menedzher-12-08</b>', reply_markup=ourrulesbackbtnmk)

async def orderandplacepr_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>https://telegra.ph/Razmeshchenie-oplaty-i-reklamy-12-08 </b>', reply_markup=ourrulesbackbtnmk)

async def zastroy_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>https://telegra.ph/Zastrojshchiki-12-08</b>', reply_markup=ourrulesbackbtnmk)

async def avans_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>https://telegra.ph/Avanszadatok-12-08</b>', reply_markup=ourrulesbackbtnmk)

async def howtodogovor_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>https://telegra.ph/Kak-zaklyuchit-dogovor-12-08</b>', reply_markup=ourrulesbackbtnmk)

async def instructions_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>https://telegra.ph/Obucheniya-12-08</b>', reply_markup=ourrulesbackbtnmk)


async def missionsandmoral_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>https://telegra.ph/Missiya-i-cennosti-12-08</b>', reply_markup=ourrulesbackbtnmk)


def register_rules(dp: Dispatcher):
    dp.register_callback_query_handler(rules_inline, lambda c: c.data == 'our_rules', state='*')
    dp.register_callback_query_handler(officeManager_inline, lambda c: c.data == 'officemanagerfuncs', state='*')
    dp.register_callback_query_handler(loer_inline, lambda c: c.data == 'loer', state='*')
    dp.register_callback_query_handler(goodday_inline, lambda c: c.data == 'gooddaymanager', state='*')
    dp.register_callback_query_handler(orderandplacepr_inline, lambda c: c.data == 'orderandplacepr', state='*')
    dp.register_callback_query_handler(zastroy_inline, lambda c: c.data == 'zastroy', state='*')
    dp.register_callback_query_handler(avans_inline, lambda c: c.data == 'avans/zadatok', state='*')
    dp.register_callback_query_handler(howtodogovor_inline, lambda c: c.data == 'howtodogovor', state='*')
    dp.register_callback_query_handler(instructions_inline, lambda c: c.data == 'ruleinstruct', state='*')
    dp.register_callback_query_handler(missionsandmoral_inline, lambda c: c.data == 'rulesmissions', state='*')