from datetime import datetime, timedelta

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.callback_data import CallbackData

from bot.aiogram_calendar import simple_cal_callback, SimpleCalendar
from bot.tgbot.databases.pay_db import *
from bot.tgbot.keyboards.inline import *
from bot.tgbot.misc.states import *
from config import logger_bot


def is_within_next_week(timestamp):
    current_date = datetime.now().date()
    week_later = current_date + timedelta(days=7)

    # Конвертируем временную метку в объект datetime
    date_from_timestamp = datetime.fromtimestamp(timestamp).date()

    # Проверяем, находится ли дата в пределах следующих 7 дней
    return current_date <= date_from_timestamp <= week_later


async def meeting_inlineRoom(cb: CallbackQuery, state: FSMContext):
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
                await state.set_state(createMeetingStates.roomnum_state.state)
                await cb.message.edit_text('<b>Выберите этаж:</b>', reply_markup=floornummk)
        else:
            await cb.answer('⭕ Сначала оплатите подписку!', show_alert=True)


async def meeting_inlineFloor(cb: CallbackQuery, state: FSMContext):
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
                await state.set_state(createMeetingStates.roomnum_state.state)
                if cb.data == 'floornum_1':
                    await cb.message.edit_text('<b>Выберите переговорную (10 этаж):</b>', reply_markup=firstfloor_roomnummk)
                    await state.update_data(floor_state=cb.data)
                elif cb.data == 'floornum_2':
                    await cb.message.edit_text('<b>Выберите переговорную (8 этаж):</b>', reply_markup=secondfloor_roomnummk)
                    await state.update_data(floor_state=cb.data)
        else:
            await cb.answer('⭕ Сначала оплатите подписку!', show_alert=True)


async def meeting_inlineCalendar(cb: CallbackQuery, state: FSMContext):
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
                data = await state.get_data()
                floornum = data['floor_state']
                roomnum = cb.data.split('_')[1]
                await state.update_data(roomnum_state=roomnum)
                await cb.message.edit_text('<b>Выберите дату проведения встречи:</b>', reply_markup=await SimpleCalendar().start_calendar(floornum=floornum))
        else:
            await cb.answer('⭕ Сначала оплатите подписку!', show_alert=True)


async def process_simple_calendar(callback_query: CallbackQuery, callback_data: CallbackData, state: FSMContext):
    banned = getBannedUserId(callback_query.from_user.id)
    if banned == 0:
        roomnum_data = await state.get_data()
        floornum = roomnum_data['floor_state']
        selected, date = await SimpleCalendar().process_selection(callback_query, callback_data, floornum)
        if selected:
            meeting_id = get_random_string(8)
            roomnum = roomnum_data['roomnum_state']

            createMeeting(callback_query.from_user.id, str(
                date.strftime("%d/%m/%Y")), meeting_id, roomnum)
            await callback_query.message.edit_text(f'<b>Выберите все необходимые для вас промежутки времени:</b>', reply_markup=genTimePartsMk(meeting_id))


async def process_timechoiced(callback_query: CallbackQuery, state: FSMContext):
    banned = getBannedUserId(callback_query.from_user.id)
    if banned == 0:
        roomnum_data = await state.get_data()
        roomnum = roomnum_data['roomnum_state']

        meeting_id = callback_query.data.split('_')[2]
        new_time1 = callback_query.data.split('_')[1]
        new_time = f'{new_time1};'
        res = editTimes(meeting_id, new_time, int(roomnum))
        if res == 'busied':
            date = checkMeetingDay(meeting_id, roomnum)
            occupied_times = checkTimeExists1(date, roomnum)
            print(f'{occupied_times=}')
            name = occupied_times[new_time1]
            print(f'{name=}')
            if callback_query.from_user.username == name:
                new_time = str(new_time)
                meeting_id1 = checkmeetingid(
                    callback_query.from_user.id, date, roomnum, new_time)
                deleteMeeting(meeting_id1)
                await callback_query.answer('Ваша запись отменена', show_alert=True)
                await callback_query.message.edit_text(f'<b>Выберите все необходимые для вас промежутки времени:</b>', reply_markup=genTimePartsMk(meeting_id))
            else:
                # Старый код
                # await callback_query.answer(f'Данное время занято! @{name}', show_alert=True)
                await callback_query.message.answer(
                    f'Данное время занято!\n[Написать пользователю](https://t.me/{name})',
                    parse_mode="Markdown"
                )
        else:
            await callback_query.message.edit_text(f'<b>Выберите все необходимые для вас промежутки времени:</b>', reply_markup=genTimePartsMk(meeting_id))


async def process_timesave(callback_query: CallbackQuery, state: FSMContext):
    roomnum_data = await state.get_data()
    roomnum = roomnum_data['roomnum_state']
    meeting_id = callback_query.data.split('_')[1]
    meeting_day = str(checkMeetingDay(meeting_id, roomnum))
    now_time = checkTimes(meeting_id)
    times = checkTimes(meeting_id).split(';')
    full_data = ' '.join(times)
    await state.finish()
    if now_time == 'Empty':
        await callback_query.message.delete()
        await callback_query.message.answer("Главное меню", reply_markup=mainmenu_mk)
    else:
        await callback_query.message.delete()
        await callback_query.message.answer(f'<b>Отлично, переговорная забронирована на {meeting_day} на время {full_data}\nЖдем вас !!!</b>', reply_markup=mainmenu_mk)
        makeMeetCompleted(
            meeting_id, callback_query.from_user.username, roomnum)


async def checkrentsdate(callback_query: CallbackQuery):
    rows = getAllMeetings()
    # Формируем список бронирований на каждую дату
    bookings = []
    for row in rows:
        meeting_id, user_id, status, date, times, roomnum = row

        date_format = "%d/%m/%Y"

        # Преобразуем строку в объект datetime
        date_object = datetime.strptime(date, date_format)

        # Получаем временную метку
        timestamp = date_object.timestamp()

        formatted_date = datetime.strptime(
            date, '%d/%m/%Y').strftime('%d.%m.%Y')
        formatted_times = times.replace(';', '; ')
        result = is_within_next_week(timestamp)
        if result and formatted_times != 'None' and status != 0:
            bookings.append((formatted_date, formatted_times))

    # Сортируем список бронирований по ближайшей дате к текущей дате
    bookings = sorted(
        bookings, key=lambda x: datetime.strptime(x[0], '%d.%m.%Y'))

    # Формируем сообщение с отсортированными бронированиями
    message = "<b>📝 Бронирования переговорной на ближайшие 7 дней:</b>\n\n"
    for booking in bookings:
        formatted_date, formatted_times = booking
        message += f"<b>Переговорная: {roomnum}</b>\n"
        message += f"<b>Дата: {formatted_date}</b>\n"
        message += f"Время: <i>{formatted_times}</i>\n\n"
    await callback_query.message.edit_text(message, reply_markup=mainmenu_mk)


def register_meeting(dp: Dispatcher):
    dp.register_callback_query_handler(
        meeting_inlineRoom, lambda c: c.data == 'rent_meetingoffice', state='*')
    dp.register_callback_query_handler(
        meeting_inlineFloor, lambda c: 'floornum_' in c.data, state='*')
    dp.register_callback_query_handler(
        meeting_inlineCalendar, lambda c: 'roomnum_' in c.data, state='*')
    dp.register_callback_query_handler(
        process_simple_calendar, simple_cal_callback.filter(), state='*')
    dp.register_callback_query_handler(
        process_timechoiced, lambda c: 'writetime_' in c.data, state='*')
    dp.register_callback_query_handler(
        process_timesave, lambda c: 'savetimes_' in c.data, state='*')
    dp.register_callback_query_handler(
        checkrentsdate, lambda c: 'check_meetingoffice' in c.data, state='*')
