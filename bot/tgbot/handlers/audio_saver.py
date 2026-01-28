import os

from aiogram import Dispatcher, types
from aiogram.types import ContentType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import AUDIO_DB_PATH, BASE_DIR, logger_bot, DB_TYPE
from bot.tgbot.models.audio_saver_models import Base, AudioFile
from bot.tgbot.services.speech_faster_whisper import process_voice_with_faster_whisper

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


HOST_TURN = os.getenv('HOST_TURN', 'False').strip().lower() == 'true'
if HOST_TURN:
    CHANNEL_ID = int(os.getenv('PAID_CHANNEL', ''))
else:
    CHANNEL_ID = int(os.getenv('TEST_PAID_CHANNEL', ''))


# Настройка БД
# Используем правильный формат URL в зависимости от типа БД
if DB_TYPE == "postgres":
    # PostgreSQL использует полный URL
    engine = create_engine(AUDIO_DB_PATH, echo=False)
else:
    # SQLite использует путь к файлу
    engine = create_engine(f"sqlite:///{AUDIO_DB_PATH}", echo=False)

# Создаем таблицы (оборачиваем в try-except для безопасности)
try:
    Base.metadata.create_all(engine)
except Exception as e:
    logger_bot.warning(f"Не удалось создать таблицы (возможно они уже существуют): {e}")

SessionLocal = sessionmaker(bind=engine)

SAVE_DIR = os.path.join(BASE_DIR, "bot", "downloaded_audio")
os.makedirs(SAVE_DIR, exist_ok=True)


async def save_audio_from_channel(message: types.Message):
    session = SessionLocal()
    try:
        # Определяем файл
        if message.audio:
            file_id = message.audio.file_id
            file_unique_id = message.audio.file_unique_id
            file_name = message.audio.file_name or f"{file_unique_id}.mp3"
        else:
            file_id = message.voice.file_id
            file_unique_id = message.voice.file_unique_id
            file_name = f"{file_unique_id}.ogg"

        # Получаем файл с сервера Telegram
        file_info = await message.bot.get_file(file_id)
        local_path = os.path.join(SAVE_DIR, file_name)
        await message.bot.download_file(file_info.file_path, destination=local_path)

        audio_text = await process_voice_with_faster_whisper(local_path)

        # Сохраняем в БД
        audio_entry = AudioFile(
            file_id=file_id,
            file_unique_id=file_unique_id,
            file_name=file_name,
            file_path=local_path,
            audio_text=audio_text,
            message_id=message.message_id,
            channel_id=message.chat.id
        )
        session.add(audio_entry)
        session.commit()
        logger_bot.info(f"Сохранено: {file_name}")
    except Exception as e:
        logger_bot.error(f"Ошибка при сохранении аудио: {e}")
    finally:
        session.close()


def register_audio_saver_handlers(dp: Dispatcher):
    dp.register_channel_post_handler(
        save_audio_from_channel,
        content_types=[ContentType.AUDIO, ContentType.VOICE],
        chat_id=CHANNEL_ID
    )
