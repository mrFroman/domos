from aiogram import Dispatcher
from aiogram.types import CallbackQuery, Message
from aiogram.dispatcher import FSMContext

from bot.tgbot.keyboards.inline import *
from bot.tgbot.databases.pay_db import *
from bot.tgbot.misc.states import *


async def feedback_inline(cb: CallbackQuery, state: FSMContext):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.edit_text('<b>Отправьте ваш отзыв или опишите проблему</b>', reply_markup=mainmenu_mk)
        await state.set_state(feedBackStates.text.state)


async def feedbackTextInputed(message: Message, state: FSMContext):
    await state.finish()
    adm_msg = f'''
<b>Новый вопрос в поддержку от @{message.from_user.username}</b>

<code>Сообщение:</code> {message.text}'''
    sendLogToAdmMk(adm_msg, feedbackAdmGen(message.from_user.id))
    await message.answer('<i>Спасибо, ваш отзыв отправлен администраторам</i>', reply_markup=mainmenu_mk)


async def feedbackadmin_inline(cb: CallbackQuery, state: FSMContext):
    user_id = cb.data.split('_')[1]
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        await cb.message.answer('<b>Отправьте ваш ответ:</b>', reply_markup=mainmenu_mk)
        await state.set_state(feedBackStates.admin_userid.state)
        await state.update_data(admin_userid=user_id)
        await state.set_state(feedBackStates.admin_text.state)


async def feedbackAdminTextInputed(message: Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = user_data['admin_userid']
    user_msg = f'''
<b>Новый ответ от поддержки</b>

<code>Сообщение:</code> {message.text}'''
    sendLogToUser(user_msg, user_id)
    await message.answer('<i>Спасибо, ваш ответ отправлен пользователю</i>', reply_markup=mainmenu_mk)


def register_feedback(dp: Dispatcher):
    dp.register_callback_query_handler(
        feedback_inline, lambda c: c.data == 'feedback', state='*')
    dp.register_callback_query_handler(
        feedbackadmin_inline, lambda c: 'feedbackanswer_' in c.data, state='*')
    dp.register_message_handler(
        feedbackAdminTextInputed, state=feedBackStates.admin_text)
    dp.register_message_handler(feedbackTextInputed, state=feedBackStates.text)
