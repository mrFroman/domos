from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.tgbot.keyboards.inline import *
from bot.tgbot.databases.pay_db import *
from bot.tgbot.misc.states import *


async def searchuser_inline(cb: CallbackQuery, state: FSMContext):
    await state.finish()
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
            await cb.message.edit_text('<b>Отправьте username юзера БЕЗ (@):</b>', reply_markup=mainmenu_mk)
            await searchUserStates.username.set()
    else:
        await cb.answer('⭕ Сначала оплатите подписку!', show_alert=True)

async def texted_username(message: Message, state: FSMContext):
    await state.update_data(username=message.text)
    user_id, pay_status, rank, username = checkUserExistsUsername(message.text)
        

    if user_id != 'empty':
        if int(pay_status) == 1:
            endts = float(getUserEndPay(user_id))
            enddate = datetime.datetime.fromtimestamp(endts)
            pay_status = f'Оплачено до <code>{enddate}</code>'
        else:
            pay_status = 'Не оплачено'
        
        if int(rank) == 1:
            rank = 'Админ'
        else:
            rank = 'Юзер'
        banned = getBannedUserId(user_id)
        if banned == 1:
            banned = 'Забанен'
        else:
            banned = 'Не забанен'
        msg = f'''
<code>Пользователь</code> - @{username}        

<code>Telegram ID</code> - <code>{user_id}</code>        
<code>Статус оплаты</code> - {pay_status}        
<code>Ранг</code> - {rank}
<code>Бан</code> - {banned}'''
        await message.answer(msg, reply_markup=genUserEditMk(user_id))

    else:
        await message.answer('Пользователь не найден', reply_markup=mainmenu_mk)



async def banuser_inline(cb: CallbackQuery, state: FSMContext):
    await state.finish()
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
            user_id = cb.data.split('_')[1]
            banUser(user_id)
            await cb.message.edit_text('<b>Пользователь забанен!</b>', reply_markup=mainmenu_mk)
    else:
        await cb.answer('⭕ Сначала оплатите подписку!', show_alert=True)


async def unbanuser_inline(cb: CallbackQuery, state: FSMContext):
    await state.finish()
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
            user_id = cb.data.split('_')[1]
            unbanUser(user_id)
            await cb.message.edit_text('<b>Пользователь разблокирован!</b>', reply_markup=mainmenu_mk)
    else:
        await cb.answer('⭕ Сначала оплатите подписку!', show_alert=True)


async def takeusersub_inline(cb: CallbackQuery, state: FSMContext):
    await state.finish()
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
            user_id = cb.data.split('_')[1]
            takeUserSub(user_id)
            await cb.message.edit_text('<b>Подписка отключена!</b>', reply_markup=mainmenu_mk)
    else:
        await cb.answer('⭕ Сначала оплатите подписку!', show_alert=True)

async def changeadminuser_inline(cb: CallbackQuery, state: FSMContext):
    await state.finish()
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
            user_id = cb.data.split('_')[1]
            res = changeUserAdmin(user_id)
            if res == 'admined':
                await cb.message.edit_text('<b>Пользователь стал админом!</b>', reply_markup=mainmenu_mk)
            else:
                await cb.message.edit_text('<b>Пользователь разжалован!</b>', reply_markup=mainmenu_mk)
    else:
        await cb.answer('⭕ Сначала оплатите подписку!', show_alert=True)


async def givesub_inline(cb: CallbackQuery, state: FSMContext):
        await state.finish()

        username = cb.from_user.username
        if username == None:
            await cb.message.edit_text('''
    Для корректной работы необходимо в настройках изменить имя пользователя!
    Как это сделать:
    Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
    После изменения @username войдите в бот по ссылке еще раз и нажмите /start
    ''')
        else:
            user_id = cb.data.split('_')[1]
            await searchUserStates.user_id.set()
            await state.update_data(user_id=user_id)
            await cb.message.edit_text('<b>Введите до какого (номер месяца) дать подписку:</b>', reply_markup=mainmenu_mk)


async def texted_useridGiveSub(message: Message, state: FSMContext):
    await state.update_data(months=message.text)
    user_data = await state.get_data()
    user_id = user_data['user_id']
    print(user_id)
    giveUserSub(user_id, int(message.text))
    await message.answer('Успешно!', reply_markup=genUserEditMk(user_id))

def register_searchuser(dp: Dispatcher):
    dp.register_callback_query_handler(searchuser_inline, lambda c: c.data == 'searchuser', state='*')
    dp.register_callback_query_handler(banuser_inline, lambda c: 'banuser_' in c.data, state='*')
    dp.register_callback_query_handler(unbanuser_inline, lambda c: 'unbanneduser_' in c.data, state='*')
    dp.register_callback_query_handler(changeadminuser_inline, lambda c: 'changeadmin_' in c.data, state='*')
    dp.register_callback_query_handler(givesub_inline, lambda c: 'givesub_' in c.data, state='*')
    dp.register_callback_query_handler(takeusersub_inline, lambda c: 'takesub_' in c.data, state='*')
    dp.register_message_handler(texted_username, state=searchUserStates.username)
    dp.register_message_handler(texted_useridGiveSub, state=searchUserStates.user_id)
