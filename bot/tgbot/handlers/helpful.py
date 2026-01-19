import datetime
import os
from pathlib import Path
from typing import Union

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import CallbackQuery, InputFile, Message

from bot.tgbot.databases.pay_db import *
from bot.tgbot.keyboards.inline import *
from bot.tgbot.services.photo_yandex_gpt import *
from bot.tgbot.fast_app.function import (
    send_passport_edit_link,
    send_passport_edit_link1,
)
from config import BASE_DIR

path = str(Path(__file__).parents[2])


class PassportStates(StatesGroup):
    waiting_for_passport_photo = State()
    waiting_for_registration_photo = State()
    waiting_for_client_passport = State()
    waiting_for_client_registration = State()


class ContractStates(StatesGroup):
    waiting_confirmation = State()
    waiting_correction = State()
    doc_type = State()


async def start_contract_process1(callback_query: CallbackQuery, state: FSMContext):
    """Начинает процесс создания договора с проверкой и запросом недостающих данных"""
    user_id = callback_query.from_user.id
    data = await state.get_data()
    doc_type = data.get("doc_type")
    await state.update_data(doc_type=doc_type)

    # Проверяем данные риелтора
    rieltor_data = get_rieltor_data(user_id)
    if not rieltor_data:
        await callback_query.message.answer("❌ Не найдены данные паспорта риелтора")
        await callback_query.message.answer(
            "Пожалуйста, отправьте фото или PDF основного разворота паспорта риелтора"
        )
        await PassportStates.waiting_for_passport_photo.set()
        return

    # Проверяем данные клиента
    client_data = get_last_client_data(user_id)
    if not client_data:
        await callback_query.message.answer("❌ Не найдены данные паспорта клиента")
        await callback_query.message.answer(
            "Пожалуйста, отправьте фото или PDF основного разворота паспорта клиента"
        )
        await PassportStates.waiting_for_client_passport.set()
        return

    # Формируем сообщение с данными
    text = (
        "📄 Данные паспорта риелтора:\n"
        f"{format_passport_data(rieltor_data)}\n\n"
        "📄 Данные паспорта клиента:\n"
        f"{format_passport_data(client_data)}"
    )

    # Сохраняем оригинальные данные в FSM
    passport_data = {
        "doc_type": doc_type,
        "rieltor_last_name": rieltor_data["last_name"],
        "rieltor_first_name": rieltor_data["first_name"],
        "rieltor_middle_name": rieltor_data["middle_name"],
        "rieltor_birth_date": rieltor_data["birth_date"],
        "rieltor_passport_series": rieltor_data["passport_series"],
        "rieltor_passport_number": rieltor_data["passport_number"],
        "rieltor_issued_by": rieltor_data["issued_by"],
        "rieltor_issue_date": rieltor_data["issue_date"],
        "rieltor_registration_address": rieltor_data["registration_address"],
        "client_last_name": client_data["last_name"],
        "client_first_name": client_data["first_name"],
        "client_middle_name": client_data["middle_name"],
        "client_birth_date": client_data["birth_date"],
        "client_passport_series": client_data["passport_series"],
        "client_passport_number": client_data["passport_number"],
        "client_issued_by": client_data["issued_by"],
        "client_issue_date": client_data["issue_date"],
        "client_registration_address": client_data["registration_address"],
        # ... все остальные поля
    }
    # Генерируем договор
    await send_passport_edit_link1(callback_query, passport_data, state)
    logger_bot.info(f"Договор сгенерирован  .\n\n{text}")


async def start_contract_process(message: Message, state: FSMContext):
    """Начинает процесс создания договора с проверкой и запросом недостающих данных"""
    logger_bot.info(
        f"Начинает процесс создания договора от пользователя {message.from_user.id}"
    )
    user_id = message.from_user.id
    data = await state.get_data()
    doc_type = data.get("doc_type")

    # Проверяем данные риелтора
    rieltor_data = get_rieltor_data(user_id)
    if not rieltor_data:
        await message.answer("❌ Не найдены данные паспорта риелтора")
        await message.answer(
            "Пожалуйста, отправьте фото или PDF основного разворота паспорта риелтора"
        )
        await PassportStates.waiting_for_passport_photo.set()
        return

    # Проверяем данные клиента
    client_data = get_last_client_data(user_id)
    if not client_data:
        await message.answer("❌ Не найдены данные паспорта клиента")
        await message.answer(
            "Пожалуйста, отправьте фото или PDF основного разворота паспорта клиента"
        )
        await PassportStates.waiting_for_client_passport.set()
        return

    # Формируем сообщение с данными
    text = (
        "📄 Данные паспорта риелтора:\n"
        f"{format_passport_data(rieltor_data)}\n\n"
        "📄 Данные паспорта клиента:\n"
        f"{format_passport_data(client_data)}\n\n"
        "Проверьте данные и отправьте КОПИЮ этого сообщения с исправлениями (если нужно).\n"
        "Можно исправлять только значения после двоеточий!\n\nЕсли исправление не требуются, просто отправьте копию этого сообщения для подтверждения!"
    )

    # Сохраняем оригинальные данные в FSM
    passport_data = {
        "rieltor_last_name": rieltor_data["last_name"],
        "rieltor_first_name": rieltor_data["first_name"],
        "rieltor_middle_name": rieltor_data["middle_name"],
        "rieltor_birth_date": rieltor_data["birth_date"],
        "rieltor_passport_series": rieltor_data["passport_series"],
        "rieltor_passport_number": rieltor_data["passport_number"],
        "rieltor_issued_by": rieltor_data["issued_by"],
        "rieltor_issue_date": rieltor_data["issue_date"],
        "rieltor_registration_address": rieltor_data["registration_address"],
        "client_last_name": client_data["last_name"],
        "client_first_name": client_data["first_name"],
        "client_middle_name": client_data["middle_name"],
        "client_birth_date": client_data["birth_date"],
        "client_passport_series": client_data["passport_series"],
        "client_passport_number": client_data["passport_number"],
        "client_issued_by": client_data["issued_by"],
        "client_issue_date": client_data["issue_date"],
        "client_registration_address": client_data["registration_address"],
        # ... все остальные поля
    }
    # Генерируем договор
    await send_passport_edit_link(message, passport_data, state)


async def process_correction(message: Message, state: FSMContext):
    """Обрабатывает исправленные данные"""
    data = await state.get_data()
    original_text = data["original_text"]
    realtor_data = data["rieltor_data"]
    client_data = data["client_data"]
    user_id = message.from_user.id
    data = await state.get_data()
    doc_type = data.get("doc_type")
    await state.update_data(doc_type=doc_type)
    # Проверяем, что сообщение - копия оригинала
    if not message.text.startswith("📄 Данные паспорта риелтора:"):
        await message.answer(
            "❌ Пожалуйста, отправьте КОПИЮ предыдущего сообщения с исправлениями\n\nЕсли исправление не требуются, просто отправьте копию сообщения с данными для подтверждения!"
        )
        return

    # Парсим исправленные данные
    try:
        corrected_data = parse_corrected_data(original_text, message.text)

        # Применяем изменения
        for field, (old_val, new_val) in corrected_data["rieltor"].items():
            if old_val != new_val:
                update_passport_data(
                    message.from_user.id, field, new_val, is_client=False
                )

        for field, (old_val, new_val) in corrected_data["client"].items():
            if old_val != new_val:
                update_passport_data(
                    message.from_user.id, field, new_val, is_client=True
                )
        passport_data = {
            "rieltor_last_name": realtor_data["last_name"],
            "rieltor_first_name": realtor_data["first_name"],
            "rieltor_middle_name": realtor_data["middle_name"],
            "rieltor_birth_date": realtor_data["birth_date"],
            "rieltor_passport_series": realtor_data["passport_series"],
            "rieltor_passport_number": realtor_data["passport_number"],
            "rieltor_issued_by": realtor_data["issued_by"],
            "rieltor_issue_date": realtor_data["issue_date"],
            "rieltor_registration_address": realtor_data["registration_address"],
            "client_last_name": client_data["last_name"],
            "client_first_name": client_data["first_name"],
            "client_middle_name": client_data["middle_name"],
            "client_birth_date": client_data["birth_date"],
            "client_passport_series": client_data["passport_series"],
            "client_passport_number": client_data["passport_number"],
            "client_issued_by": client_data["issued_by"],
            "client_issue_date": client_data["issue_date"],
            "client_registration_address": client_data["registration_address"],
            # ... все остальные поля
        }
        # Генерируем договор
        await send_passport_edit_link(message, passport_data, state)
        # await message.answer("✅ Данные обновлены! Генерирую договор...")

        # contract_path = await generate_contract(user_id, state)
        # await message.answer_document(open(contract_path, 'rb'))

    except ValueError as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    finally:
        await state.finish()


async def cmd_start_passport(cb: CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id  # Получаем ID пользователя
    client_name = check_passport_client_exists(user_id)
    doc_type = cb.data.split("_")[-1]

    # Сохраняем тип документа в state
    await state.update_data(doc_type=doc_type)
    if check_passport_exists(user_id):
        if client_name != 1:
            new_client_mk = InlineKeyboardMarkup(row_width=1)
            positive_answer = InlineKeyboardButton(
                "Да", callback_data=f"cariant_1_{doc_type}"
            )
            new_client = InlineKeyboardButton(
                "Завести нового клиента", callback_data=f"cariant_2_{doc_type}"
            )
            contracts_list_back_btn = InlineKeyboardButton(
                "◀️ Назад", callback_data="create_contract"
            )
            new_client_mk.add(positive_answer, new_client, contracts_list_back_btn)
            await cb.message.edit_text(
                f"<b>вы хотите продолжить заполнять договор с {client_name}:</b>",
                reply_markup=new_client_mk,
            )
        else:
            await cb.message.edit_text(
                "Пожалуйста, отправьте фото или PDF основного разворота паспорта клиента"
            )
            await PassportStates.waiting_for_client_passport.set()
    else:
        await cb.message.edit_text(
            "Пожалуйста, отправьте фото или PDF основного разворота паспорта риелтора"
        )
        await PassportStates.waiting_for_passport_photo.set()


async def new_client_function(cb: CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    parts = cb.data.split("_")
    # variant = parts[-2]  # "1" или "2"
    doc_type = parts[-1]  # тип документа

    # Сохраняем тип документа в state
    await state.update_data(doc_type=doc_type)

    await cb.message.edit_text(
        "Пожалуйста, отправьте фото или PDF основного разворота паспорта клиента"
    )
    await PassportStates.waiting_for_client_passport.set()


async def process_client_passport(message: Message, state: FSMContext):
    # Сохраняем фото
    user_id = message.from_user.id
    if message.photo:
        # Фото — сохраняем как jpg
        # photo_path = f"{path}/passports/{user_id}_client_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        photo_path = os.path.join(
            BASE_DIR,
            "bot",
            "passports",
            f"{user_id}_client_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
        )
        await message.photo[-1].download(photo_path)
    elif message.document:
        # Документ — определяем расширение
        file_name = message.document.file_name
        # если вдруг нет расширения, по умолчанию pdf
        ext = Path(file_name).suffix or ".pdf"
        # photo_path = f"{path}/passports/{user_id}_client_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
        photo_path = os.path.join(
            BASE_DIR,
            "bot",
            "passports",
            f"{user_id}_client_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}",
        )
        await message.document.download(photo_path)
    else:
        await message.reply(
            "❌ Не удалось определить тип файла. Пришлите фото или PDF."
        )
        return

    # Отправляем сообщение о начале обработки
    processing_msg = await message.reply("🔍 Анализирую изображение...")

    try:
        # Скачиваем фото
        data = await state.get_data()
        doc_type = data.get("doc_type")
        model = "passport"

        # Обрабатываем фото
        raw_text = vision_api.extract_text_from_image(photo_path, model)
        if not raw_text:
            await processing_msg.edit_text(
                "Не удалось распознать текст. Попробуйте другое фото."
            )
            return

        # Извлекаем структурированные данные
        passport_data = gpt_processor.extract_passport_data(raw_text)

        # Обновляем состояние
        await state.update_data(
            passport_data=passport_data, passport_photo=photo_path, doc_type=doc_type
        )

        # Редактируем исходное сообщение с результатом
        await processing_msg.edit_text(
            "✅ Данные паспорта распознаны!\nТеперь отправьте фото или PDF страницы с регистрацией клиента"
        )

        # Устанавливаем следующее состояние
        await PassportStates.waiting_for_client_registration.set()

    except Exception as e:
        logger_bot.error(f"Error processing passport: {str(e)}")
        await processing_msg.edit_text(
            "⚠️ Произошла ошибка при обработке. Попробуйте еще раз."
        )
        return


async def process_client_registration(message: Message, state: FSMContext):
    # Сохраняем фото
    user_id = message.from_user.id
    if message.photo:
        # Фото — сохраняем как jpg
        # photo_path = f"{path}/passports/registration_{user_id}_client_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        photo_path = os.path.join(
            BASE_DIR,
            "bot",
            "passports",
            f"registration_{user_id}_client_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
        )
        await message.photo[-1].download(photo_path)
    elif message.document:
        # Документ — определяем расширение
        file_name = message.document.file_name
        # если вдруг нет расширения, по умолчанию pdf
        ext = Path(file_name).suffix or ".pdf"
        # photo_path = f"{path}/passports/registration_{user_id}_client_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
        photo_path = os.path.join(
            BASE_DIR,
            "bot",
            "passports",
            f"registration_{user_id}_client_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}",
        )
        await message.document.download(photo_path)
    else:
        await message.reply(
            "❌ Не удалось определить тип файла. Пришлите фото или PDF."
        )
        return

    # Отправляем сообщение о начале обработки
    processing_msg = await message.reply("🔍 Анализирую изображение с регистрацией...")

    try:
        # Скачиваем фото
        data = await state.get_data()
        doc_type = data.get("doc_type")

        await state.update_data(doc_type=doc_type)

        # Обрабатываем фото регистрации
        model = "handwritten"
        raw_text = vision_api.extract_text_from_image(photo_path, model)

        if not raw_text:
            await processing_msg.edit_text(
                "❌ Не удалось распознать текст. Попробуйте другое фото."
            )
            return

        # Извлекаем структурированные данные
        registration_data = gpt_processor.extract_registration_data(raw_text)

        user_data = await state.get_data()
        passport_data = user_data["passport_data"]
        id1 = f"{user_id}_client"

        # Сохраняем в БД
        save_passport(passport_data, id1, registration_data, is_client=True)

        # Редактируем сообщение о завершении обработки
        await processing_msg.edit_text("✅ Данные регистрации успешно распознаны!")

        # Переходим к формированию договора
        await start_contract_process(message, state)

    except Exception as e:
        logger_bot.error(f"Ошибка при обработке регистрации: {str(e)}")
        await processing_msg.edit_text(
            "⚠️ Произошла ошибка при обработке. Попробуйте еще раз."
        )


async def process_passport_photo(message: Message, state: FSMContext):
    logger_bot.info(f"Получаем фото паспорта от риелтора {message.from_user.id}")
    user_id = message.from_user.id
    if message.photo:
        logger_bot.info(f"Найдено фото паспорта")
        # photo_path = f"{path}/passports/{user_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        photo_path = os.path.join(
            BASE_DIR,
            "bot",
            "passports",
            f"{user_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
        )
        await message.photo[-1].download(photo_path)
        logger_bot.info(f"Фото сохранено в {photo_path}")
    elif message.document:
        logger_bot.info(f"Найден документ паспорта")
        file_name = message.document.file_name
        ext = Path(file_name).suffix or ".pdf"
        # photo_path = f"{path}/passports/{user_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
        photo_path = os.path.join(
            BASE_DIR,
            "bot",
            "passports",
            f"{user_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}",
        )
        await message.document.download(photo_path)
        logger_bot.info(f"Документ сохранен в {photo_path}")
    else:
        await message.reply(
            "❌ Не удалось определить тип файла. Пришлите фото или PDF."
        )
        logger_bot.error("❌ Не удалось определить тип файла. Пришлите фото или PDF.")
        return

    # Отправляем сообщение о начале обработки
    processing_msg = await message.reply("🔍 Анализирую изображение паспорта...")

    try:
        logger_bot.info(f"Скачиваем файл")
        data = await state.get_data()
        doc_type = data.get("doc_type")
        await state.update_data(doc_type=doc_type)

        model = "passport"
        raw_text = vision_api.extract_text_from_image(photo_path, model)
        logger_bot.info(f"Распознанный текст с файла: {raw_text}")

        if not raw_text:
            await processing_msg.edit_text(
                "❌ Не удалось распознать текст. Попробуйте другое фото."
            )
            logger_bot.error(
                "❌ Не удалось распознать текст. Либо ИИ вернул пустой текст."
            )
            return

        # Извлекаем структурированные данные
        passport_data = gpt_processor.extract_passport_data(raw_text)
        logger_bot.info(f"Извлеченные данные паспорта: {passport_data}")

        # Обновляем состояние
        await state.update_data(
            passport_data=passport_data, passport_photo=photo_path, doc_type=doc_type
        )

        # Редактируем сообщение о завершении обработки
        await processing_msg.edit_text(
            "✅ Данные паспорта успешно распознаны!\nТеперь отправьте фото или PDF страницы с регистрацией"
        )

        # Устанавливаем следующее состояние
        await PassportStates.waiting_for_registration_photo.set()

    except Exception as e:
        logger_bot.error(f"Ошибка при обработке паспорта: {str(e)}")
        await processing_msg.edit_text(
            "⚠️ Произошла ошибка при обработке. Попробуйте еще раз."
        )


async def process_registration_photo(message: Message, state: FSMContext):
    logger_bot.info("Сохраняем фото регистрации")
    user_id = message.from_user.id
    if message.photo:
        logger_bot.info(f"Найдено фото регистрации")
        # photo_path = f"{path}/passports/registration_{user_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        photo_path = os.path.join(
            BASE_DIR,
            "bot",
            "passports",
            f"registration_{user_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
        )
        await message.photo[-1].download(photo_path)
        logger_bot.info(f"Документ сохранен в {photo_path}")
    elif message.document:
        logger_bot.info(f"Найден документ регистрации")
        file_name = message.document.file_name
        ext = Path(file_name).suffix or ".pdf"
        # photo_path = f"{path}/passports/registration_{user_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
        photo_path = os.path.join(
            BASE_DIR,
            "bot",
            "passports",
            f"registration_{user_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}",
        )
        await message.document.download(photo_path)
        logger_bot.info(f"Документ сохранен в {photo_path}")
    else:
        await message.reply(
            "❌ Не удалось определить тип файла. Пришлите фото или PDF."
        )
        logger_bot.error("❌ Не удалось определить тип файла. Пришлите фото или PDF.")
        return

    # Отправляем сообщение о начале обработки
    processing_msg = await message.reply("🔍 Анализирую изображение регистрации...")

    try:
        logger_bot.info(f"Скачиваем файл")
        data = await state.get_data()
        doc_type = data.get("doc_type")

        await state.update_data(doc_type=doc_type)

        # Обрабатываем фото регистрации
        model = "handwritten"
        raw_text = vision_api.extract_text_from_image(photo_path, model)
        logger_bot.info(f"Распознанный текст с файла: {raw_text}")
        if not raw_text:
            await processing_msg.edit_text(
                "❌ Не удалось распознать текст. Попробуйте другое фото."
            )
            logger_bot.error(
                "❌ Не удалось распознать текст. Либо ИИ вернул пустой текст."
            )
            return

        # Извлекаем структурированные данные
        registration_data = gpt_processor.extract_registration_data(raw_text)
        user_data = await state.get_data()
        passport_data = user_data["passport_data"]
        logger_bot.info(f"Извлеченные данные регистрации: {registration_data}")
        logger_bot.info(f"Извлеченные данные паспорта: {passport_data}")
        # Сохраняем в БД
        save_passport(passport_data, user_id, registration_data, is_client=False)

        # Редактируем сообщение о завершении обработки
        await processing_msg.edit_text(
            "✅ Данные регистрации успешно распознаны!\nПожалуйста, отправьте фото или PDF основного разворота паспорта клиента"
        )

        # Устанавливаем следующее состояние
        await PassportStates.waiting_for_client_passport.set()

    except Exception as e:
        logger_bot.error(f"Ошибка при обработке регистрации: {str(e)}")
        await processing_msg.edit_text(
            "⚠️ Произошла ошибка при обработке. Попробуйте еще раз."
        )


async def helpful_inline(cb: CallbackQuery):
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
        payed = getUserPay(cb.from_user.id)
        if payed == 1:
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
                try:
                    await cb.message.edit_text(
                        "<b>Инструкция</b>", reply_markup=helpful_mk
                    )
                except:
                    await cb.message.reply("<b>Инструкция</b>", reply_markup=helpful_mk)
        else:
            await cb.answer("⭕ Сначала оплатите подписку!", show_alert=True)


async def helpfullinks_inline(cb: CallbackQuery):
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
        payed = getUserPay(cb.from_user.id)
        if payed == 1:
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
                    "<b>Нажмите на кнопку, чтобы открыть ссылку:</b>",
                    reply_markup=links_mk,
                )
        else:
            await cb.answer("⭕ Сначала оплатите подписку!", show_alert=True)


async def helpfulpartners_inline(cb: CallbackQuery):
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
        payed = getUserPay(cb.from_user.id)
        if payed == 1:
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
                    "<b>Нажмите на кнопку, чтобы открыть ссылку:</b>",
                    reply_markup=partnersmk,
                )
        else:
            await cb.answer("⭕ Сначала оплатите подписку!", show_alert=True)


async def conturAccess_inline(cb: CallbackQuery):
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
        payed = getUserPay(cb.from_user.id)
        if payed == 1:
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
<i>Доступ к сервису проверок</i>
https://reestro.kontur.ru/
domosagent@yandex.ru

Пароль - <code>Domos1234</code>"""
                await cb.message.edit_text(msg, reply_markup=helpfulbackbtnmk)
        else:
            await cb.answer("⭕ Сначала оплатите подписку!", show_alert=True)


async def companyHistory_inline(cb: CallbackQuery):
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
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
                "<b>https://telegra.ph/Istoriya-kompanii-12-08</b>",
                reply_markup=helpfulbackbtnmk,
            )


async def helpfulblanks_inline(cb: CallbackQuery):
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
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
                "<b>Нажмите на кнопку, чтобы открыть бланк:</b>",
                reply_markup=helpfulblanks_mk,
            )


async def command_dogovor_handler(update: Union[Message, CallbackQuery]):
    """Универсальный обработчик для команды /dogovor и callback create_contract"""
    # Определяем тип входящего объекта и извлекаем необходимые данные
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
                await message.answer(
                    "<b>Нажмите на кнопку, чтобы открыть бланк:</b>",
                    reply_markup=helpfulblanks1_mk,
                )
        else:
            await message.answer("⭕ Сначала оплатите подписку!")


async def giveblank_inline(cb: CallbackQuery):
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
        avanssogl_personal_doc = InputFile(
            os.path.join(
                BASE_DIR, "bot", "blanks", "Авансовое соглашение(бланк-ФЛ).docx"
            )
        )
        avanssogl_IP_doc = InputFile(
            os.path.join(
                BASE_DIR, "bot", "blanks", "Авансовое соглашение(бланк-ИП).docx"
            )
        )

        dogovorarendi_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Договор аренды(бланк).docx")
        )

        ipoteka_personal_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Ипотека(бланк-ФЛ).docx")
        )
        ipoteka_IP_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Ипотека(бланк-ИП).docx")
        )
        ipoteka_self_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Ипотека(бланк-Самозанятый).docx")
        )

        obmen_personal_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Обмен(бланк-ФЛ).docx")
        )
        obmen_IP_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Обмен(бланк-ИП).docx")
        )
        obmen_self_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Обмен(бланк-Самозанятый).docx")
        )

        pdkp_doc = InputFile(
            os.path.join(
                BASE_DIR, "bot", "blanks", "ПДКП_без поручительства(бланк).docx"
            )
        )

        podbor_personal_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Подбор(бланк-ФЛ).docx")
        )
        podbor_IP_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Подбор(бланк-ИП).docx")
        )
        podbor_self_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Подбор(бланк-Самозанятый).docx")
        )

        prodazha_personal_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Продажа(бланк-ФЛ).docx")
        )
        prodazha_IP_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Продажа(бланк-ИП).docx")
        )
        prodazha_self_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Продажа(бланк-Самозанятый).docx")
        )

        rastorg_doc = InputFile(
            os.path.join(
                BASE_DIR, "bot", "blanks", "Расторжение договора услуг(бланк).doc"
            )
        )

        ursopr_personal_doc = InputFile(
            os.path.join(
                BASE_DIR, "bot", "blanks", "Юридическое сопровождение(бланк-ФЛ).docx"
            )
        )
        ursopr_IP_doc = InputFile(
            os.path.join(
                BASE_DIR, "bot", "blanks", "Юридическое сопровождение(бланк-ИП).docx"
            )
        )
        ursopr_self_doc = InputFile(
            os.path.join(
                BASE_DIR,
                "bot",
                "blanks",
                "Юридическое сопровождение(бланк-Самозанятый).docx",
            )
        )

        rastorgavans_doc = InputFile(
            os.path.join(
                BASE_DIR, "bot", "blanks", "Соглашение о расторжении аванса(бланк).docx"
            )
        )

        uvedzavishshort_doc = InputFile(
            os.path.join(
                BASE_DIR,
                "bot",
                "blanks",
                "Уведомление завышения-занижения краткое(бланк).docx",
            )
        )
        uvedzavishlong_doc = InputFile(
            os.path.join(
                BASE_DIR,
                "bot",
                "blanks",
                "Уведомление завышения-занижения полное(бланк).docx",
            )
        )
        uvedpereplan_doc = InputFile(
            os.path.join(
                BASE_DIR, "bot", "blanks", "Уведомление о перепланировке(бланк).doc"
            )
        )
        certificate_of_completed_works_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Акт выполненных работ(бланк).doc")
        )
        consent_processing_doc = InputFile(
            os.path.join(BASE_DIR, "bot", "blanks", "Согласие на обработку(бланк).doc")
        )

        alert_for_personal = (
            "Внимание! Предпринимательская деятельность не может осуществляться физическим лицом! "
            + "Данный бланк договора рекомендуем использовать только для редактирования. Чтобы избежать нарушений "
            + "и штрафов от государственных органов рекомендуем работать в качестве индивидуального предпринимателя либо "
            + "самозанятого. Пройти регистрацию можно у администрации."
        )
        if cb.data == "helpfulblank1":
            await cb.message.answer_document(
                avanssogl_personal_doc, caption=alert_for_personal
            )
            await cb.message.answer_document(
                avanssogl_IP_doc, reply_markup=helpfulbackbtnmk
            )
            logger_bot.info(
                f"Бланк авансового соглашения отправлены пользователю @{username}"
            )

        elif cb.data == "helpfulblank2":
            await cb.message.answer_document(
                dogovorarendi_doc,
                caption=alert_for_personal,
                reply_markup=helpfulbackbtnmk,
            )
            logger_bot.info(
                f"Бланк договора аренды отправлены пользователю @{username}"
            )

        elif cb.data == "helpfulblank3":
            await cb.message.answer_document(
                ipoteka_personal_doc, caption=alert_for_personal
            )
            await cb.message.answer_document(ipoteka_IP_doc)
            await cb.message.answer_document(
                ipoteka_self_doc, reply_markup=helpfulbackbtnmk
            )
            logger_bot.info(f"Бланки ипотеки отправлены пользователю @{username}")

        elif cb.data == "helpfulblank4":
            await cb.message.answer_document(
                obmen_personal_doc, caption=alert_for_personal
            )
            await cb.message.answer_document(obmen_IP_doc)
            await cb.message.answer_document(
                obmen_self_doc, reply_markup=helpfulbackbtnmk
            )
            logger_bot.info(f"Бланки обмена отправлены пользователю @{username}")

        elif cb.data == "helpfulblank5":
            await cb.message.answer_document(
                pdkp_doc, caption=alert_for_personal, reply_markup=helpfulbackbtnmk
            )
            logger_bot.info(f"Бланк ПДКП отправлены пользователю @{username}")

        elif cb.data == "helpfulblank5_1":
            await cb.message.answer_document(
                pdkp_doc, caption=alert_for_personal, reply_markup=helpfulbackbtnmk
            )
            logger_bot.info(f"Бланк ПДКП отправлены пользователю @{username}")

        elif cb.data == "helpfulblank6":
            await cb.message.answer_document(
                podbor_personal_doc, caption=alert_for_personal
            )
            await cb.message.answer_document(podbor_IP_doc)
            await cb.message.answer_document(
                podbor_self_doc, reply_markup=helpfulbackbtnmk
            )
            logger_bot.info(f"Бланки подбора отправлены пользователю @{username}")

        elif cb.data == "helpfulblank7":
            await cb.message.answer_document(
                prodazha_personal_doc, caption=alert_for_personal
            )
            await cb.message.answer_document(prodazha_IP_doc)
            await cb.message.answer_document(
                prodazha_self_doc, reply_markup=helpfulbackbtnmk
            )
            logger_bot.info(f"Бланки продажи отправлены пользователю @{username}")

        elif cb.data == "helpfulblank8":
            await cb.message.answer_document(
                rastorg_doc, caption=alert_for_personal, reply_markup=helpfulbackbtnmk
            )
            logger_bot.info(
                f"Бланк расторжения договора услуг отправлены пользователю @{username}"
            )

        elif cb.data == "helpfulblank9":
            await cb.message.answer_document(
                ursopr_personal_doc, caption=alert_for_personal
            )
            await cb.message.answer_document(ursopr_IP_doc)
            await cb.message.answer_document(
                ursopr_self_doc, reply_markup=helpfulbackbtnmk
            )
            logger_bot.info(
                f"Бланк юридического сопровождения отправлены пользователю @{username}"
            )

        elif cb.data == "helpfulblank10":
            await cb.message.answer_document(
                rastorgavans_doc,
                caption=alert_for_personal,
                reply_markup=helpfulbackbtnmk,
            )

        elif cb.data == "helpfulblank11":
            await cb.message.answer_document(
                uvedzavishshort_doc,
                caption=alert_for_personal,
                reply_markup=helpfulbackbtnmk,
            )

        elif cb.data == "helpfulblank11_1":
            await cb.message.answer_document(
                uvedzavishshort_doc,
                caption=alert_for_personal,
                reply_markup=helpfulbackbtnmk,
            )

        elif cb.data == "helpfulblank12":
            await cb.message.answer_document(
                uvedzavishlong_doc,
                caption=alert_for_personal,
                reply_markup=helpfulbackbtnmk,
            )

        elif cb.data == "helpfulblank12_1":
            await cb.message.answer_document(
                uvedzavishlong_doc,
                caption=alert_for_personal,
                reply_markup=helpfulbackbtnmk,
            )

        elif cb.data == "helpfulblank13":
            await cb.message.answer_document(
                uvedpereplan_doc,
                caption=alert_for_personal,
                reply_markup=helpfulbackbtnmk,
            )

        elif cb.data == "helpfulblank13_1":
            await cb.message.answer_document(
                uvedpereplan_doc,
                caption=alert_for_personal,
                reply_markup=helpfulbackbtnmk,
            )

        elif cb.data == "helpfulblank14":
            await cb.message.answer_document(
                certificate_of_completed_works_doc,
                caption=alert_for_personal,
                reply_markup=helpfulbackbtnmk,
            )
        elif cb.data == "helpfulblank15":
            await cb.message.answer_document(
                consent_processing_doc,
                caption=alert_for_personal,
                reply_markup=helpfulbackbtnmk,
            )


async def helpfulcontacts_inline(cb: CallbackQuery):
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
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
                "<b>Контакты:</b>", reply_markup=genContactsList()
            )


async def pogotovkakv_inline(cb: CallbackQuery):
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
        pogotovkakv_doc = InputFile(
            f"{path}/blanks/Подготовка_квартиры_к_съёмке_ДОМОС.pdf"
        )
        await cb.message.answer_document(
            pogotovkakv_doc,
            caption="<b>Подготовка квартиры к съемке</b>",
            reply_markup=mainmenuanswer_btn,
        )


async def pamyatka_inline(cb: CallbackQuery):
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
        pamyatka_doc = InputFile(f"{path}/blanks/Памятка справка и ТК (1).pdf")
        await cb.message.answer_document(
            pamyatka_doc,
            caption="<b>Памятка по заполнению ТК и 2НДФЛ</b>",
            reply_markup=mainmenuanswer_btn,
        )


async def helpfulipotek_inline(cb: CallbackQuery):
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
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
                "<b>https://docs.google.com/spreadsheets/d/1JBUPAAUilnkoSYkEd5z0tvZulYOVrnCGXgvNnHvyITw/edit</b>",
                reply_markup=helpfulbackbtnmk,
            )


def register_helpful(dp: Dispatcher):
    dp.register_callback_query_handler(
        helpful_inline, lambda c: c.data == "Helpful", state="*"
    )
    dp.register_callback_query_handler(
        conturAccess_inline, lambda c: c.data == "konturaccess", state="*"
    )
    dp.register_callback_query_handler(
        helpfullinks_inline, lambda c: c.data == "helpfullinks", state="*"
    )
    dp.register_callback_query_handler(
        companyHistory_inline, lambda c: c.data == "helpfulcompanyhistory", state="*"
    )
    dp.register_callback_query_handler(
        helpfulblanks_inline, lambda c: c.data == "helpfulblancs", state="*"
    )
    # dp.register_callback_query_handler(helpfulipotek_inline, lambda c: c.data == 'helpfilipotekcalendar', state='*')
    dp.register_callback_query_handler(
        helpfulcontacts_inline, lambda c: c.data == "contacntshelpful", state="*"
    )
    dp.register_callback_query_handler(
        giveblank_inline, lambda c: "helpfulblank" in c.data, state="*"
    )
    dp.register_callback_query_handler(
        pamyatka_inline, lambda c: "helpfultk2ndfl" in c.data, state="*"
    )
    dp.register_callback_query_handler(
        pogotovkakv_inline, lambda c: "helpfulhomephoto" in c.data, state="*"
    )
    dp.register_callback_query_handler(
        helpfulpartners_inline, lambda c: "partnersbonuses" in c.data, state="*"
    )
    dp.register_callback_query_handler(
        cmd_start_passport, lambda c: "blank_" in c.data, state="*"
    )
    dp.register_callback_query_handler(
        start_contract_process1, lambda c: "cariant_1" in c.data, state="*"
    )
    dp.register_callback_query_handler(
        new_client_function, lambda c: "cariant_2" in c.data, state="*"
    )
    dp.register_message_handler(
        process_passport_photo,
        content_types=["photo", "document"],
        state=PassportStates.waiting_for_passport_photo,
    )
    dp.register_message_handler(
        process_registration_photo,
        content_types=["photo", "document"],
        state=PassportStates.waiting_for_registration_photo,
    )
    dp.register_message_handler(
        process_client_passport,
        content_types=["photo", "document"],
        state=PassportStates.waiting_for_client_passport,
    )
    dp.register_message_handler(
        process_client_registration,
        content_types=["photo", "document"],
        state=PassportStates.waiting_for_client_registration,
    )
    dp.register_message_handler(
        process_correction, state=ContractStates.waiting_confirmation
    )
    dp.register_message_handler(
        command_dogovor_handler, commands=["dogovor"], state="*"
    )
    dp.register_callback_query_handler(
        command_dogovor_handler, lambda c: c.data == "create_contract", state="*"
    )
