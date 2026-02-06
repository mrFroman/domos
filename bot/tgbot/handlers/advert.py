import pytz
from datetime import datetime
from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.tgbot.services.speech_yandex import process_voice_with_yandex
from bot.tgbot.databases.pay_db import *
from config import logger_bot


# Установка часового пояса Екатеринбурга
YEKATERINBURG_TZ = pytz.timezone("Asia/Yekaterinburg")


class AdvertStates(StatesGroup):
    CHOOSING_TYPE = State()
    ENTERING_TEXT = State()
    RECORDING_VOICE = State()
    ADDING_MEDIA = State()
    CHOOSING_PLATFORMS = State()
    SPECIFYING_PLATFORMS = State()


async def start_advert_request(update: Union[Message, CallbackQuery]):
    if isinstance(update, Message):
        user_id = update.from_user.id
        username = update.from_user.username
        message = update
    else:  # CallbackQuery
        user_id = update.from_user.id
        username = update.from_user.username
        message = update.message

    banned = getBannedUserId(user_id)
    if banned == 0:
        payed = getUserPay(user_id)
        if payed == 1:
            if username is None:
                await message.answer(
                    """
    Для корректной работы необходимо в настройках изменить имя пользователя!
    Как это сделать:
    Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
    После изменения @username войдите в бот по ссылке еще раз и нажмите /start
    """
                )
            else:
                await AdvertStates.CHOOSING_TYPE.set()
                await message.answer(
                    "Выберите способ создания рекламного объявления:",
                    reply_markup=advert_type_kb(),
                )
        else:
            await message.answer("⭕ Сначала оплатите подписку!")


def advert_type_kb():
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("✍️ Написать текст", callback_data="advert_text"),
        types.InlineKeyboardButton(
            "🎤 Записать голосовое", callback_data="advert_voice"
        ),
    )


def platforms_kb():
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("Все площадки", callback_data="platforms_all"),
        types.InlineKeyboardButton("Указать свои", callback_data="platforms_custom"),
    )


async def process_advert_text_choice(cb: CallbackQuery, state: FSMContext):
    await AdvertStates.ENTERING_TEXT.set()
    await cb.message.answer("Напишите текст для рекламного объявления:")


async def process_advert_voice_choice(cb: CallbackQuery, state: FSMContext):
    await AdvertStates.RECORDING_VOICE.set()
    await cb.message.answer("Запишите голосовое сообщение с текстом для рекламы:")


async def process_advert_text(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["request_type"] = "text"
        data["original_text"] = message.text
        data["processed_text"] = message.text

    await AdvertStates.ADDING_MEDIA.set()
    await message.answer(
        "Вы можете приложить до 30 медиафайлов (фото, видео, документы). "
        "Отправьте их по одному или нажмите /skip",
        reply_markup=types.ReplyKeyboardRemove(),
    )


async def process_advert_voice(message: types.Message, state: FSMContext):
    if not message.voice:
        await message.answer("Пожалуйста, отправьте голосовое сообщение")
        return

    async with state.proxy() as data:
        data["request_type"] = "voice"
        data["voice_file_id"] = message.voice.file_id

    # Обработка голосового с указанием, что это для рекламы
    processed_text = await process_voice_with_yandex(
        voice_file_id=message.voice.file_id,
        bot=message.bot,
        context="Это текст для рекламного объявления. Отформатируй его соответствующим образом.",
    )

    async with state.proxy() as data:
        data["processed_text"] = processed_text

    # await message.answer(f"Текст вашего объявления:\n\n{processed_text}")
    await AdvertStates.ADDING_MEDIA.set()
    await message.answer(
        "Вы можете приложить до 30 медиафайлов (фото, видео, документы). "
        "Отправьте их по одному или нажмите /skip",
        reply_markup=types.ReplyKeyboardRemove(),
    )


async def process_advert_media(message: types.Message, state: FSMContext):
    content_types = [
        types.ContentType.PHOTO,
        types.ContentType.VIDEO,
        types.ContentType.DOCUMENT,
    ]

    if message.content_type not in content_types:
        await message.answer("Пожалуйста, отправьте фото, видео или документ")
        return

    async with state.proxy() as data:
        if "media" not in data:
            data["media"] = []

        if len(data["media"]) >= 30:
            await message.answer("Максимальное количество файлов - 30")
            return

        # Для фото берем самое большое доступное разрешение
        if message.content_type == types.ContentType.PHOTO:
            file_id = message.photo[-1].file_id
        else:
            file_id = message[message.content_type].file_id

        data["media"].append({"file_id": file_id, "type": message.content_type})

        remaining = 30 - len(data["media"])
        await message.answer(
            f"Файл принят. Можно приложить ещё {remaining} файлов, если хотите закончить нажмите /skip"
        )


async def finish_advert_media(message: types.Message, state: FSMContext):
    await AdvertStates.CHOOSING_PLATFORMS.set()
    await message.answer(
        "Выберите площадки для размещения:", reply_markup=platforms_kb()
    )


async def process_platforms_choice(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "platforms_all":
        async with state.proxy() as data:
            data["platforms"] = "Все площадки"

        await send_advert_to_manager(callback, state)
        await state.finish()

    elif callback.data == "platforms_custom":
        await AdvertStates.SPECIFYING_PLATFORMS.set()
        await callback.message.answer(
            "Укажите площадки для размещения (например: ЦИАН, Авито, Яндекс.Недвижимость):"
        )


async def process_custom_platforms(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["platforms"] = message.text

    await send_advert_to_manager(message, state)
    await state.finish()


async def send_advert_to_manager(
    update: Union[types.Message, types.CallbackQuery], state: FSMContext
):
    async with state.proxy() as data:
        # Получаем информацию о пользователе
        user_id = update.from_user.id
        user_info = get_user_info(user_id)

        # Формируем имя отправителя
        if user_info.get("full_name"):
            sender_name = user_info["full_name"]
        elif user_info.get("full_name_payments"):
            sender_name = user_info["full_name"]
        else:
            sender_name = f"Пользователь с ID {user_id}"

        # Формируем ссылку на пользователя
        username = user_info.get("full_name")
        user_link = f"@{username}"

        # ID менеджера по рекламе
        managers = ["805171682", "5023044689"]
        manager_id1 = "805171682"  # Замените на реальный ID
        manager_id = "5023044689"
        # Формируем сообщение для менеджера
        message_text = (
            f"📢 Новое рекламное объявление\n\n"
            f"👤 От: {sender_name}\n"
            f"📞 Связаться: {user_link}\n"
            f"🌐 Площадки: {data['platforms']}\n\n"
            f"📝 Текст объявления:\n{data['processed_text']}"
        )
        now = datetime.datetime.now(YEKATERINBURG_TZ)
        save_request_to_db(
            "advert", now, data["processed_text"], sender_name, user_link
        )
        try:
            # Отправляем основное сообщение
            if isinstance(update, types.CallbackQuery):
                for manager in managers:
                    await update.bot.send_message(manager, message_text)
                    logger_bot.info(f"Отправлено сообщение менеджеру с ID: {manager}")
            else:
                for manager in managers:
                    await update.bot.send_message(manager, message_text)
                    logger_bot.info(f"Отправлено сообщение менеджеру с ID: {manager}")

            # Отправляем медиафайлы
            for media_item in data.get("media", []):
                if media_item["type"] == types.ContentType.PHOTO:
                    for manager in managers:
                        await update.bot.send_photo(
                            chat_id=manager, photo=media_item["file_id"]
                        )
                        logger_bot.info(f"Отправлено фото менеджеру с ID: {manager}")
                elif media_item["type"] == types.ContentType.VIDEO:
                    for manager in managers:
                        await update.bot.send_video(
                            chat_id=manager, video=media_item["file_id"]
                        )
                        logger_bot.info(f"Отправлено видео менеджеру с ID: {manager}")
                else:
                    for manager in managers:

                        await update.bot.send_document(
                            chat_id=manager, document=media_item["file_id"]
                        )
                        logger_bot.info(f"Отправлен документ менеджеру с ID: {manager}")

            # Отправляем голосовое сообщение, если есть
            if data.get("voice_file_id"):
                for manager in managers:
                    await update.bot.send_voice(
                        chat_id=manager,
                        voice=data["voice_file_id"],
                        caption="Оригинальное голосовое сообщение",
                    )
                    logger_bot.info(
                        f"Отправлено голосовое сообщение менеджеру с ID: {manager}"
                    )

            # Отправляем подтверждение пользователю
            if isinstance(update, types.CallbackQuery):
                await update.message.answer(
                    "✅ Ваше рекламное объявление отправлено менеджеру!"
                )
                logger_bot.info(f"Отправлено потверждение пользователю с ID: {user_id}")
            else:
                await update.answer(
                    "✅ Ваше рекламное объявление отправлено менеджеру!\n чтобы вернуться в главное меню нажмите /start"
                )
                logger_bot.info(f"Отправлено потверждение пользователю с ID: {user_id}")

        except Exception as e:
            logger_bot.error(f"Ошибка при отправке рекламного объявления: {e}")
            if isinstance(update, types.CallbackQuery):
                await update.answer(
                    "Ошибка при отправке объявления",
                    show_alert=True,
                )
            else:
                await update.answer("Ошибка при отправке объявления")


def register_advert_handlers(dp: Dispatcher):
    dp.register_message_handler(start_advert_request, commands="advert", state="*")
    dp.register_callback_query_handler(
        process_advert_text_choice,
        lambda c: c.data == "advert_text",
        state=AdvertStates.CHOOSING_TYPE,
    )
    dp.register_callback_query_handler(
        process_advert_voice_choice,
        lambda c: c.data == "advert_voice",
        state=AdvertStates.CHOOSING_TYPE,
    )
    dp.register_message_handler(
        finish_advert_media, commands="skip", state=AdvertStates.ADDING_MEDIA
    )
    dp.register_message_handler(
        process_advert_text,
        content_types=types.ContentType.TEXT,
        state=AdvertStates.ENTERING_TEXT,
    )
    dp.register_message_handler(
        process_advert_voice,
        content_types=types.ContentType.VOICE,
        state=AdvertStates.RECORDING_VOICE,
    )
    dp.register_message_handler(
        process_advert_media,
        content_types=types.ContentType.ANY,
        state=AdvertStates.ADDING_MEDIA,
    )
    dp.register_callback_query_handler(
        process_platforms_choice,
        lambda c: c.data.startswith("platforms_"),
        state=AdvertStates.CHOOSING_PLATFORMS,
    )
    dp.register_message_handler(
        process_custom_platforms, state=AdvertStates.SPECIFYING_PLATFORMS
    )
