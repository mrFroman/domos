import datetime

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.tgbot.databases.pay_db import *
from bot.tgbot.keyboards.inline import *
from bot.tgbot.misc.states import *


async def eventsMenu(cb: CallbackQuery):
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
            await cb.message.edit_text('<b>Список событий:</b>', reply_markup=genEventsMk(cb.from_user.id))


async def showevent_inline(cb: CallbackQuery):
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text('''
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
''')
    else:
        event_id = cb.data.split('_')[1]
        event = getEventId(event_id)
        desc = event[1]
        date = event[2]
        link = event[4]
        name = event[5]
        photo = str(event[6])
        print(date)
        dt_object = datetime.datetime.fromtimestamp(date).strftime('%d-%m-%Y %H:%M')
        msg = f'''
<code>🧿 Название:</code> {name}

<code>📝 Описание:</code> {desc}     
<code>⏰ Дата:</code> {dt_object}    
<code>🔗 Ссылка:</code> {link}                
'''
        MAX_MESSAGE_LENGTH = 4096  # лимит Telegram на длину текста
        MAX_CAPTION_LENGTH = 1024  # лимит на caption фото

        if photo == '0':
            if len(msg) <= MAX_MESSAGE_LENGTH:
                await cb.message.answer(msg, reply_markup=GenEventShowMK(cb.from_user.id, event_id))
            else:
                # Разбиваем длинное сообщение на части по пробелам
                while len(msg) > MAX_MESSAGE_LENGTH:
                    msg_part = msg[:MAX_MESSAGE_LENGTH].rsplit(' ', 1)[0]
                    await cb.message.answer(msg_part, reply_markup=GenEventShowMK(cb.from_user.id, event_id))
                    msg = msg[len(msg_part):].lstrip()

                # Отправляем оставшуюся часть
                if msg:
                    await cb.message.answer(msg, reply_markup=GenEventShowMK(cb.from_user.id, event_id))

        else:
            if len(msg) <= MAX_CAPTION_LENGTH:
                await cb.message.answer_photo(photo, msg, reply_markup=GenEventShowMK(cb.from_user.id, event_id))
            else:
                caption_part = msg[:MAX_CAPTION_LENGTH].rsplit(' ', 1)[0]
                remaining_part = msg[len(caption_part):].lstrip()

                await cb.message.answer_photo(photo, caption_part, reply_markup=GenEventShowMK(cb.from_user.id, event_id))

                # Отправляем остаток длинного caption отдельными сообщениями (по необходимости разбивая)
                while len(remaining_part) > MAX_MESSAGE_LENGTH:
                    text_part = remaining_part[:MAX_MESSAGE_LENGTH].rsplit(' ', 1)[
                        0]
                    await cb.message.answer(text_part, reply_markup=GenEventShowMK(cb.from_user.id, event_id))
                    remaining_part = remaining_part[len(text_part):].lstrip()

                if remaining_part:
                    await cb.message.answer(remaining_part, reply_markup=GenEventShowMK(cb.from_user.id, event_id))


# ADD EVENT
async def addEvent_inline(cb: CallbackQuery, state: FSMContext):
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
        await cb.message.edit_text('<b>Введите заголовок события:</b>', reply_markup=mainmenu_mk)
        await state.set_state(addEventStates.title.state)


async def addEventTitled(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer('<i>Введите полное название события:</i>', reply_markup=mainmenu_mk)
    await state.set_state(addEventStates.name.state)


async def addEventNamed(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer('<i>Введите описание события:</i>', reply_markup=mainmenu_mk)
    await state.set_state(addEventStates.desc.state)


async def addEventDesced(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer('<i>Введите дату события в формате 25.03.2023 11:00</i>', reply_markup=mainmenu_mk)
    await state.set_state(addEventStates.date.state)


async def addEventDated(message: Message, state: FSMContext):
    ts = time.mktime(datetime.datetime.strptime(
        message.text, "%d.%m.%Y %H:%M").timetuple())
    await state.update_data(date=ts)
    await state.set_state(addEventStates.timestr.state)
    await state.update_data(timestr=message.text)
    await message.answer('<i>Отправьте фото с ссылкой/только ссылку, а если нет ссылки отправьте "-"</i>', reply_markup=mainmenu_mk)
    await state.set_state(addEventStates.link.state)


async def addEventLinked(message: Message, state: FSMContext):
    try:
        id_photo = message.photo[-1].file_id
    except:
        id_photo = 0
    await state.update_data(link=message.text)
    user_data = await state.get_data()
    event_id = get_random_string(7)
    title = user_data['title']
    name = user_data['name']
    desc = user_data['desc']
    date = user_data['date']
    link = user_data['link']
    timestr = user_data['timestr']
    createEvent(event_id, desc, date, title, link, name, id_photo)
    users = getAllUsersForAd()
    await message.answer('<i>Событие создано!</i>', reply_markup=mainmenu_mk)
    for i in users:
        res = sendLogToUser(
            f'Пользователь @{message.from_user.username} создал мероприятие "{title}" на время: {timestr}', i[0])
    await state.finish()


async def delEventHandler(cb: CallbackQuery):
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
            evid = cb.data.split('_')[1]
            delEvent(evid)
            await cb.message.answer('<b>Событие успешно удалено!</b>', reply_markup=genEventsMk(cb.from_user.id))


def regevents(dp: Dispatcher):
    dp.register_callback_query_handler(
        eventsMenu, lambda c: c.data == 'eventsmenu', state='*')
    dp.register_callback_query_handler(
        addEvent_inline, lambda c: c.data == 'createeventmenu', state='*')
    dp.register_callback_query_handler(
        showevent_inline, lambda c: 'checkevent_' in c.data, state='*')
    dp.register_callback_query_handler(
        delEventHandler, lambda c: 'delevent_' in c.data, state='*')
    dp.register_message_handler(addEventTitled, state=addEventStates.title)
    dp.register_message_handler(addEventNamed, state=addEventStates.name)
    dp.register_message_handler(addEventDesced, state=addEventStates.desc)
    dp.register_message_handler(addEventDated, state=addEventStates.date)
    dp.register_message_handler(
        addEventLinked, state=addEventStates.link, content_types=["photo", "text"])
