import os
import uuid
from typing import Union

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InputFile

from bot.tgbot.keyboards.options import generation_options_keyboard
from bot.tgbot.services.gemini_client import generate_plan_from_image


# Хранилище ID последних изображений
latest_images = {}  # user_id -> path


class ImageStates(StatesGroup):
    waiting_image = State()


async def start_image_handler(update: Union[Message, CallbackQuery]):
    if isinstance(update, Message):
        await update.answer(
            "🧩 В одном сообщении отправьте планировку для обработки и указания для ИИ что требуется сделать."
        )
    else:
        await update.message.answer(
            "📤 Пришли новое изображение и указания для ИИ что требуется сделать."
        )
    await ImageStates.waiting_image.set()


async def handle_image(message: Message, state: FSMContext):
    text = message.caption or message.text
    await state.update_data(user_message=text)
    if not text:
        text = ""
        # await message.answer(
        #     "⚠️ Вы не добавили текстовые указания.\n"
        #     "Отправьте изображение вместе с описанием в одном сообщении."
        # )
        # await start_image_handler(message)
        # return

    if not message.photo:
        await message.answer(
            "⚠️ Вы не отправили изображение.\n"
            "Отправьте изображение вместе с описанием в одном сообщении."
        )
        await start_image_handler(message)
        return

    try:
        photo_id = message.photo[-1].file_id
    except Exception:
        await message.answer("⚠️ Не удалось обработать фото. Повторите попытку.")
        await start_image_handler(message)
        return

    # Сохраняем изображение локально
    file = await message.bot.get_file(photo_id)
    image_path = f"images/{uuid.uuid4().hex}.jpg"
    os.makedirs("images", exist_ok=True)
    await message.bot.download_file(file.file_path, image_path)
    await state.update_data(image_path=image_path)

    user_id = message.from_user.id
    await message.answer("🧠 Обрабатываю изображение через AI, подожди немного...")
    processed_path = await generate_plan_from_image(image_path, text)
    if processed_path:
        latest_images[user_id] = image_path
        photo = InputFile(processed_path)
        await message.answer_photo(
            photo=photo,
            caption="✅ Готово! Хочешь сгенерировать снова или загрузить другое?",
            reply_markup=generation_options_keyboard(image_path),
        )
    else:
        await message.answer(
            "⚠️ Не удалось обработать изображение. Попробуй снова или пришли другое."
        )
    # await state.finish()


async def regenerate_image(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    await callback.message.edit_caption("🔁 Генерирую заново, подожди...")

    new_path = await generate_plan_from_image(
        state_data["image_path"],
        state_data.get("user_message", ""),
    )
    if new_path:
        photo = InputFile(new_path)
        await callback.message.answer_photo(
            photo=photo,
            caption="♻️ Вот новая версия чертежа!",
            reply_markup=generation_options_keyboard(state_data["image_path"]),
        )
    else:
        await callback.message.answer("❌ Ошибка при повторной генерации.")


def register_image_generator_handlers(dp: Dispatcher):
    dp.register_message_handler(
        start_image_handler,
        commands="plan",
    )
    dp.register_message_handler(
        handle_image,
        # content_types=types.ContentType.PHOTO,
        content_types=types.ContentTypes.ANY,
        state=ImageStates.waiting_image,
    )
    dp.register_callback_query_handler(
        regenerate_image,
        lambda c: c.data.startswith("regenerate:"),
        state="*",
    )
    dp.register_callback_query_handler(
        start_image_handler,
        lambda c: c.data == "upload_new",
        state="*",
    )
