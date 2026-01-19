from pathlib import Path

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message, InputFile

from bot.tgbot.databases.pay_db import *
from bot.tgbot.keyboards.inline import *
from bot.tgbot.misc.states import *
from bot.tgbot.misc.exunpaid import *
from bot.tgbot.misc.exunpaid import create_excel_advert_new


path = str(Path(__file__).parents[2])


async def settings_inline(cb: CallbackQuery, state: FSMContext):
    await state.finish()
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text(
            """
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
"""
        )
    else:
        await cb.message.edit_text("<b>Выберите опцию:</b>", reply_markup=adminMenu())


# ADD RIELTOR
async def addRieltor_inline(cb: CallbackQuery, state: FSMContext):
    await state.finish()
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text(
            """
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
"""
        )
    else:
        await cb.message.edit_text(
            "<b>Введите ФИО нового риэлтора:</b>", reply_markup=mainmenu_mk
        )
        await state.set_state(addRieltorStates.fullname.state)


async def addRieltorNamed(message: Message, state: FSMContext):
    await state.update_data(fullname=message.text)
    await message.answer(
        "<i>Введите номер телефона риелтора:</i>", reply_markup=mainmenu_mk
    )
    await state.set_state(addRieltorStates.phone.state)


async def addRieltorPhoned(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("<i>Введите email риелтора:</i>", reply_markup=mainmenu_mk)
    await state.set_state(addRieltorStates.email.state)


async def addRieltorMailed(message: Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("<i>Отправьте фото риелтора:</i>", reply_markup=mainmenu_mk)
    await state.set_state(addRieltorStates.photo.state)


async def addRieltorPhotoChosed(message: Message, state: FSMContext):
    id_photo = message.photo[-1].file_id
    await state.update_data(photo=id_photo)
    user_data = await state.get_data()
    rieltor_id = get_random_string(7)
    fio = user_data["fullname"]
    phone = user_data["phone"]
    email = user_data["email"]
    photo = user_data["photo"]
    createRieltor(rieltor_id, fio, phone, email, photo)
    await message.answer("<i>Риэлтор успешно добавлен!</i>", reply_markup=mainmenu_mk)


# ADD CONTACT
async def addContact_inline(cb: CallbackQuery, state: FSMContext):
    await state.finish()
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text(
            """
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
"""
        )
    else:
        await cb.message.edit_text(
            "<b>Введите ФИО нового контакта:</b>", reply_markup=mainmenu_mk
        )
        await state.set_state(addContactStates.fullname.state)


async def addContactNamed(message: Message, state: FSMContext):
    await state.update_data(fullname=message.text)
    await message.answer(
        "<i>Введите номер телефона контакта:</i>", reply_markup=mainmenu_mk
    )
    await state.set_state(addContactStates.phone.state)


async def addContactPhoned(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("<i>Введите email контакта:</i>", reply_markup=mainmenu_mk)
    await state.set_state(addContactStates.email.state)


async def addContactMailed(message: Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("<i>Отправьте фото контакта:</i>", reply_markup=mainmenu_mk)
    await state.set_state(addContactStates.photo.state)


async def addContactPhotoChoiced(message: Message, state: FSMContext):
    id_photo = message.photo[-1].file_id
    await state.update_data(photo=id_photo)
    await message.answer(
        "<i>Отправьте должность контакта:</i>", reply_markup=mainmenu_mk
    )
    await state.set_state(addContactStates.job.state)


async def addContactJobChosed(message: Message, state: FSMContext):
    await state.update_data(job=message.text)
    user_data = await state.get_data()
    contact_id = get_random_string(7)
    fio = user_data["fullname"]
    phone = user_data["phone"]
    email = user_data["email"]
    photo = user_data["photo"]
    job = user_data["job"]
    createContact(contact_id, fio, phone, email, photo, job)
    await message.answer("<i>Контакт успешно добавлен!</i>", reply_markup=mainmenu_mk)


# ANALYTICS
async def analytics_inline(cb: CallbackQuery, state: FSMContext):
    await state.finish()
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text(
            """
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
"""
        )
    else:
        paid = getPaidUsersCount()
        free = getFreeUsersCount()
        allint = getUsersCount()
        msg = f"""
<b>Всего людей в боте:</b> <code>{allint}</code>        
        
<b>Оплачено:</b> <code>{paid}</code>        
<b>Бесплатно:</b> <code>{free}</code>        

<code>Ниже список платных пользователей:</code>
"""
        await cb.message.edit_text(msg, reply_markup=genAnalysisMk())


# ADVERT
async def advert_inline(cb: CallbackQuery, state: FSMContext):
    await state.finish()
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text(
            """
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
"""
        )
    else:
        msg = """
<b>Рассылка</b>

В этом разделе вы можете направить одно или несколько сообщений пользователям бота.

<i>Выберите ниже, кому вы хотите направить рассылку</i>"""
        await cb.message.edit_text(msg, reply_markup=advert_mk)


async def show_advertismentAll(cb: CallbackQuery, state: FSMContext):
    await state.finish()
    await advertismentStates.adtype.set()
    await state.update_data(adtype="all")
    await advertismentStates.text.set()
    await cb.message.edit_text(
        "🌚 Отправьте текст для рассылки:", reply_markup=mainmenu_mk
    )


async def show_advertismentPaid(cb: CallbackQuery, state: FSMContext):
    await state.finish()
    await advertismentStates.adtype.set()
    await state.update_data(adtype="paid")
    await advertismentStates.text.set()
    await cb.message.edit_text(
        "🌚 Отправьте текст для рассылки:", reply_markup=mainmenu_mk
    )


async def show_advertismentFree(cb: CallbackQuery, state: FSMContext):
    await state.finish()
    await advertismentStates.adtype.set()
    await state.update_data(adtype="free")
    await advertismentStates.text.set()
    await cb.message.edit_text(
        "🌚 Отправьте текст для рассылки:", reply_markup=mainmenu_mk
    )


async def texted_advertisment(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer('🌚 Отправьте фото или видео для рассылки (если нет - отправьте 0):', reply_markup=mainmenu_mk)
    await advertismentStates.photo.set()


async def message_AdvertPhotoChoiced(message: Message, state: FSMContext):
    if message.text != '0':
        # Определяем, что прислали: фото или видео
        id_media = None
        media_type = None

        if getattr(message, "photo", None):
            id_media = message.photo[-1].file_id
            media_type = "photo"
        elif getattr(message, "video", None):
            id_media = message.video.file_id
            media_type = "video"
        else:
            await message.answer('🌚 Отправьте фото или видео для рассылки (если нет - отправьте 0):', reply_markup=mainmenu_mk)
            await advertismentStates.photo.set()
            return

        await state.update_data(photo=id_media)  # оставляем ключ "photo" чтобы не ломать остальной код
        user_data = await state.get_data()
        msg_text = user_data['text']
        adtype = user_data['adtype']
        if adtype == 'all':
            users = getAllUsersForAd()
        elif adtype == 'paid':
            users = getPaidUsersForAd()
        elif adtype == 'free':
            users = getFreeUsersForAd()
        calc = 0
        error = 0
        for i in users:
            try:
                if media_type == "photo":
                    res = sendMsgPhoto(msg_text, i[0], id_media)
                else:
                    res = sendMsgVideo(msg_text, i[0], id_media)  # нужно добавить функцию ниже
                if res == True:
                    calc += 1
                else:
                    error += 1
            except:
                pass
        await message.reply(f'🌚 Рассылка отправлена {adtype} пользователям!', reply_markup=mainmenu_mk)

    elif message.text == '0':
        user_data = await state.get_data()
        msg_text = user_data['text']
        adtype = user_data['adtype']
        if adtype == 'all':
            users = getAllUsersForAd()
        elif adtype == 'paid':
            users = getPaidUsersForAd()
        elif adtype == 'free':
            users = getFreeUsersForAd()
        calc = 0
        error = 0
        for i in users:
            try:
                res = sendLogToUser(msg_text, i[0])
                if res == True:
                    calc += 1
                else:
                    error += 1
            except:
                pass
        await message.reply(f'🌚 Рассылка отправлена {adtype} пользователям!', reply_markup=mainmenu_mk)

    await state.finish()


# ПОЛУЧАЕМ НЕОПЛАЧЕННЫХ EXCEL
async def unpaids_inline(cb: CallbackQuery, state: FSMContext):
    await state.finish()
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text(
            """
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
"""
        )
    else:
        create_excel()
        unpaids_doc = InputFile(f"{path}/tgbot/misc/dataunpaids.xlsx")
        await cb.message.answer_document(
            unpaids_doc,
            caption="<b>Список неоплаченных пользователей:</b>",
            reply_markup=mainmenu_mk,
        )


async def paids_inline(cb: CallbackQuery, state: FSMContext):
    await state.finish()
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text(
            """
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
"""
        )
    else:
        create_excel1()
        unpaids_doc = InputFile(f"{path}/tgbot/misc/datapaids.xlsx")
        await cb.message.answer_document(
            unpaids_doc,
            caption="<b>Список оплаченных пользователей:</b>",
            reply_markup=mainmenu_mk,
        )


async def lawyer_excel(cb: CallbackQuery, state: FSMContext):
    await state.finish()
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text(
            """
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
"""
        )
    else:
        create_excel_lawyer()
        unpaids_doc = InputFile(f"{path}/tgbot/misc/lawyer.xlsx")
        await cb.message.answer_document(
            unpaids_doc,
            caption="<b>Список запросов к юристу:</b>",
            reply_markup=mainmenu_mk,
        )


async def advert_excel(cb: CallbackQuery, state: FSMContext):
    await state.finish()
    username = cb.from_user.username
    if username == None:
        await cb.message.edit_text(
            """
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
"""
        )
    else:
        create_excel_advert()
        unpaids_doc = InputFile(f"{path}/tgbot/misc/advert.xlsx")
        await cb.message.answer_document(
            unpaids_doc,
            caption="<b>Отчёт в Excel файле</b>",
            reply_markup=mainmenu_mk,
        )


async def advert_excel_new(cb: CallbackQuery, state: FSMContext):
    await state.finish()
    username = cb.from_user.username
    if username is None:
        await cb.message.edit_text(
            """
Для корректной работы необходимо в настройках изменить имя пользователя!
Как это сделать:
Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
После изменения @username войдите в бот по ссылке еще раз и нажмите /start
"""
        )
    else:
        filepath = create_excel_advert_new()
        unpaids_doc = InputFile(filepath)
        await cb.message.answer_document(
            unpaids_doc,
            caption="<b>Список запросов в рекламу:</b>",
            reply_markup=mainmenu_mk,
        )


def register_settings(dp: Dispatcher):
    dp.register_callback_query_handler(
        settings_inline, lambda c: c.data == "settings", state="*"
    )
    dp.register_callback_query_handler(
        advert_inline, lambda c: c.data == "makeadvert", state="*"
    )
    dp.register_callback_query_handler(
        addRieltor_inline, lambda c: c.data == "addRieltorAdmin", state="*"
    )
    dp.register_callback_query_handler(
        addContact_inline, lambda c: c.data == "addContactAdmin", state="*"
    )
    dp.register_callback_query_handler(
        analytics_inline, lambda c: c.data == "analysis", state="*"
    )
    dp.register_callback_query_handler(
        show_advertismentAll, lambda c: c.data == "advertforall", state="*"
    )
    dp.register_callback_query_handler(
        show_advertismentPaid, lambda c: c.data == "advertforpaid", state="*"
    )
    dp.register_callback_query_handler(
        show_advertismentFree, lambda c: c.data == "advertforfree", state="*"
    )
    dp.register_callback_query_handler(
        unpaids_inline, lambda c: c.data == "getUnpaidsInline", state="*"
    )
    dp.register_callback_query_handler(
        paids_inline, lambda c: c.data == "getpaidsInline", state="*"
    )
    dp.register_callback_query_handler(
        lawyer_excel, lambda c: c.data == "lawyer_inline", state="*"
    )
    dp.register_callback_query_handler(
        advert_excel, lambda c: c.data == "advert_inline", state="*"
    )
    dp.register_callback_query_handler(
        advert_excel_new, lambda c: c.data == "advert_inline_new", state="*"
    )
    dp.register_message_handler(addRieltorNamed, state=addRieltorStates.fullname)
    dp.register_message_handler(addRieltorPhoned, state=addRieltorStates.phone)
    dp.register_message_handler(addRieltorMailed, state=addRieltorStates.email)
    dp.register_message_handler(
        addRieltorPhotoChosed, state=addRieltorStates.photo, content_types=["photo"]
    )

    dp.register_message_handler(addContactNamed, state=addContactStates.fullname)
    dp.register_message_handler(addContactPhoned, state=addContactStates.phone)
    dp.register_message_handler(addContactMailed, state=addContactStates.email)
    dp.register_message_handler(addContactJobChosed, state=addContactStates.job)
    dp.register_message_handler(
        addContactPhotoChoiced, state=addContactStates.photo, content_types=["photo"]
    )

    dp.register_message_handler(texted_advertisment, state=advertismentStates.text)
    dp.register_message_handler(message_AdvertPhotoChoiced, state=advertismentStates.photo, content_types=["photo", "video", "text"])
