import os
import pytz
from datetime import datetime
from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.tgbot.databases.pay_db import *
from bot.tgbot.keyboards.lawyer_kb import urgency_kb
from bot.tgbot.services.email_message_sender import send_email
from bot.tgbot.services.speech_yandex import process_voice_with_yandex

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


HOST_TURN = os.getenv("HOST_TURN", "False").strip().lower() == "true"
# Установка часового пояса Екатеринбурга
YEKATERINBURG_TZ = pytz.timezone("Asia/Yekaterinburg")

if HOST_TURN:
    LAWYER_IDS = [
        i.strip() for i in os.getenv("LAWYER_IDS", "").split(",") if i.strip()
    ]
else:
    LAWYER_IDS = [
        i.strip() for i in os.getenv("TEST_LAWYER_IDS", "").split(",") if i.strip()
    ]


class LawyerStates(StatesGroup):
    CHOOSING_TYPE = State()
    ENTERING_TEXT = State()
    RECORDING_VOICE = State()
    ADDING_DOCUMENTS = State()
    CHOOSING_URGENCY = State()
    AWAITING_QUESTION = State()


async def start_lawyer_request(message: types.Message):
    await LawyerStates.AWAITING_QUESTION.set()
    await message.answer(
        "Вы можете отправить ваш вопрос голосовым сообщением или текстом в следующем сообщении"
    )


async def start_lawyer_request(update: Union[Message, CallbackQuery]):
    # await LawyerStates.AWAITING_QUESTION.set()
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
                await LawyerStates.AWAITING_QUESTION.set()
                if isinstance(update, Message):
                    await update.answer(
                        "Опишите какой документ вам нужен, опишите все детали, стороны, предмет, суммы и прочее.\n\n"
                        "Вы можете отправить ваш вопрос голосовым сообщением или текстом"
                    )
                else:
                    await update.message.answer(
                        "Опишите какой документ вам нужен, опишите все детали, стороны, предмет, суммы и прочее.\n\n"
                        "Вы можете отправить ваш вопрос голосовым сообщением или текстом"
                    )
                    await update.answer()  # Просто закрыть спиннер, не выводить alert
        else:
            await message.answer("⭕ Сначала оплатите подписку!")
    # if isinstance(update, Message):
    #    await update.answer("Опишите какой документ вам нужен, опишите все детали, стороны, предмет, суммы и прочее.\n\n"
    #    "Вы можете отправить ваш вопрос голосовым сообщением или текстом")
    # else:
    #    await update.message.answer("Опишите какой документ вам нужен, опишите все детали, стороны, предмет, суммы и прочее.\n\n"
    #    "Вы можете отправить ваш вопрос голосовым сообщением или текстом")
    #    await update.answer()  # Просто закрыть спиннер, не выводить alert


async def process_text_choice(cb: CallbackQuery, state: FSMContext):
    await LawyerStates.ENTERING_TEXT.set()
    await cb.message.answer("Напишите ваш вопрос юристу:")


async def process_voice_choice(cb: CallbackQuery, state: FSMContext):
    await LawyerStates.RECORDING_VOICE.set()
    await cb.message.answer("Запишите голосовое сообщение с вашим вопросом:")


async def process_text_message(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["request_type"] = "text"
        data["original_text"] = message.text
        data["processed_text"] = message.text

    await LawyerStates.ADDING_DOCUMENTS.set()
    await message.answer(
        "Вы можете приложить до 5 файлов. Отправьте их по одному или нажмите /skip",
        reply_markup=types.ReplyKeyboardRemove(),
    )


async def process_voice_message(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["request_type"] = "voice"
        data["voice_file_id"] = message.voice.file_id

    # Здесь должна быть интеграция с Yandex SpeechKit и GPT
    processed_text = await process_voice_with_yandex(
        voice_file_id=message.voice.file_id, bot=message.bot
    )  # Передаем бота из сообщения
    async with state.proxy() as data:
        data["processed_text"] = processed_text

    await message.answer(f"Текст вашего сообщения:\n\n{processed_text}")
    await LawyerStates.ADDING_DOCUMENTS.set()
    await message.answer(
        "Вы можете приложить до 5 файлов. Отправьте их по одному или нажмите /skip",
        reply_markup=types.ReplyKeyboardRemove(),
    )


async def process_document(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    # Текущая дата
    current_date = datetime.datetime.now().strftime("%d.%m.%Y-%H-%M")

    base_dir = f"lawyer_docs/{user_id}_{current_date}"
    os.makedirs(base_dir, exist_ok=True)  # Создаём директорию, если нет

    async with state.proxy() as data:
        if "documents" not in data:
            data["documents"] = []

        if len(data["documents"]) >= 5:
            await message.answer("Максимальное количество файлов - 5")
            return

        # Получаем file_id и скачиваем файл
        file_id = message.document.file_id
        file_info = await message.bot.get_file(file_id)
        file_path = file_info.file_path

        # Локальный путь, куда сохраним файл
        local_path = os.path.join(base_dir, message.document.file_name)

        # Скачиваем файл
        await message.bot.download_file(file_path, destination=local_path)

        # Запоминаем пути скачанных файлов
        data["documents"].append(file_id)
        data["files"] = [
            os.path.join(base_dir, f)
            for f in os.listdir(base_dir)
            if os.path.isfile(os.path.join(base_dir, f))
        ]

        remaining = 5 - len(data["documents"])
        await message.answer(
            f"Файл принят. Можно приложить ещё {remaining} файлов, если хотите закончить — нажмите /skip"
        )


async def finish_documents(message: types.Message, state: FSMContext):
    await LawyerStates.CHOOSING_URGENCY.set()
    await message.answer(
        "Выберите срочность обработки вашего запроса:", reply_markup=urgency_kb()
    )


async def process_urgency(callback: types.CallbackQuery, state: FSMContext):
    urgency_map = {
        "urgency_urgent": "urgent",
        "urgency_normal": "normal",
        "urgency_complex": "complex",
    }

    urgency = urgency_map.get(callback.data)
    if not urgency:
        await callback.answer("Неверный выбор")
        return

    async with state.proxy() as data:
        data["urgency"] = urgency

        # Получаем информацию о пользователе из БД
        user_id = callback.from_user.id
        # Функция для получения данных пользователя
        user_info = get_user_info(user_id)
        # Формируем имя отправителя
        if user_info.get("full_name"):
            sender_name = user_info["full_name"]
        elif user_info.get("fullName"):
            sender_name = user_info["fullName"]
        else:
            sender_name = f"Пользователь с ID {user_id}"
        # Формируем ссылку на пользователя
        username = user_info.get("fullName")

        user_link = f"@{username}"

        now = datetime.datetime.now(YEKATERINBURG_TZ)
        save_request_to_db(
            "lawyer", now, data["processed_text"], sender_name, user_link
        )

        # Сохраняем в БД
        # save_request(request)  # Нужно реализовать эту функцию

        # Формируем сообщение для юриста
        urgency_text = {
            "urgent": "🔴 СРОЧНО (1 день)",
            "normal": "🟡 Обычный (2 дня)",
            "complex": "⚫ Сложный (3 дня)",
        }.get(urgency, "Не указано")

        message_text = (
            f"📨 Вам поступил новый запрос\n\n"
            f"👤 От: {sender_name}\n"
            f"📞 Связаться: {user_link}\n"
            f"⏱ Срочность: {urgency_text}\n\n"
            f"📝 Текст запроса:\n{data['processed_text']}"
        )

        # Отправляем сообщение на почту
        files = data.get("files", [])

        try:
            send_email(
                msg_subj=f"Заявка на юридическую помощь от {sender_name}",
                msg_text=message_text,
                files=files,
            )
            is_email_success = True
        except Exception as e:
            print(f"Ошибка отправки сообщения на почту: {e}")

        # Отправляем сообщение юристам
        try:
            for lawyer_id in LAWYER_IDS:
                await callback.bot.send_message(chat_id=lawyer_id, text=message_text)
                for doc_id in data.get("documents", []):
                    await callback.bot.send_document(chat_id=lawyer_id, document=doc_id)
                if data.get("voice_file_id"):
                    await callback.bot.send_voice(
                        chat_id=lawyer_id,
                        voice=data["voice_file_id"],
                        caption="Голосовое сообщение от пользователя",
                    )
            is_telegram_success = True
        except Exception as e:
            print(f"Ошибка при отправке сообщения юристу: {e}")
            await callback.answer(
                "Произошла ошибка при отправке запроса", show_alert=True
            )
            return

    if is_email_success and is_telegram_success:
        await callback.message.answer(
            "✅ Ваш запрос отправлен юристу. Спасибо!\n чтобы вернуться в главное менб нажмите /start"
        )
    elif is_email_success:
        await callback.message.answer(
            "✅ Ваш запрос отправлен юристу на электронную почту. Спасибо!\n чтобы вернуться в главное менб нажмите /start"
        )
    elif is_telegram_success:
        await callback.message.answer(
            "✅ Ваш запрос отправлен юристу в Telegram. Спасибо!\n чтобы вернуться в главное менб нажмите /start"
        )

    await state.finish()


def register_lawyer_handlers(dp: Dispatcher):
    dp.register_message_handler(start_lawyer_request, commands="lawyer", state="*")
    dp.register_callback_query_handler(
        start_lawyer_request, lambda c: c.data == "request_for_lawyer", state="*"
    )
    # dp.register_message_handler(process_text_choice, text="✍️ Написать текст", state=LawyerStates.CHOOSING_TYPE)
    # dp.register_message_handler(process_voice_choice, text="🎤 Записать голосовое", state=LawyerStates.CHOOSING_TYPE)
    dp.register_callback_query_handler(
        process_text_choice,
        lambda c: c.data == "text_vibot",
        state=LawyerStates.CHOOSING_TYPE,
    )
    dp.register_callback_query_handler(
        process_voice_choice,
        lambda c: c.data == "golos",
        state=LawyerStates.CHOOSING_TYPE,
    )
    dp.register_message_handler(
        process_text_message,
        state=LawyerStates.AWAITING_QUESTION,
        content_types=types.ContentType.TEXT,
    )
    dp.register_message_handler(
        process_voice_message,
        state=LawyerStates.AWAITING_QUESTION,
        content_types=types.ContentType.VOICE,
    )
    dp.register_message_handler(
        process_document,
        content_types=types.ContentType.DOCUMENT,
        state=LawyerStates.ADDING_DOCUMENTS,
    )
    dp.register_message_handler(
        finish_documents, commands="skip", state=LawyerStates.ADDING_DOCUMENTS
    )
    dp.register_callback_query_handler(
        process_urgency,
        lambda c: c.data.startswith("urgency_"),
        state=LawyerStates.CHOOSING_URGENCY,
    )
