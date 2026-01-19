import os

from aiogram import Dispatcher, types
from aiogram.types import ContentType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot.tgbot.models.chat_message_models import Base, ChatMessage
from config import USEFULL_MESSAGES_DB_PATH, logger_bot

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


HOST_TURN = os.getenv("HOST_TURN", "False").strip().lower() == "true"
if HOST_TURN:
    SUPER_GROUP_ID = int(os.getenv("SUPER_GROUP_ID", ""))
else:
    SUPER_GROUP_ID = int(os.getenv("TEST_SUPER_GROUP_ID", ""))


# Настройка БД
engine = create_engine(f"sqlite:///{USEFULL_MESSAGES_DB_PATH}", echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)


async def save_usefull_messages_channel(message: types.Message):
    session = SessionLocal()
    text = message.text
    message_id = message.message_id
    date = message.date
    topic_name = None

    try:
        # Проверяем, есть ли тема
        if message.is_topic_message:
            # Попробуем получить имя темы из reply_to_message
            if message.reply_to_message and getattr(message.reply_to_message, "forum_topic_created", None):
                topic_name = message.reply_to_message.forum_topic_created.name
            # Или достаём тему по идентификатору
            elif message.message_thread_id:
                # В aiogram 2.x нет get_forum_topic, но можно получить через get_chat
                chat_info = await message.bot.get_chat(message.chat.id)
                # Иногда Telegram присылает список topic_id → topic_name в chat_info
                topic_name = getattr(chat_info, "title", None)

    except Exception as e:
        logger_bot.warning(f"⚠ Не удалось получить имя темы: {e}")

    try:
        chat_message = ChatMessage(
            message_id=message_id,
            date=date,
            topic_name=topic_name,
            text=text,
        )
        session.add(chat_message)
        session.commit()
        logger_bot.info(f"Сохранено сообщение с id: {message_id} из темы: {topic_name}")
    except Exception as e:
        logger_bot.error(f"Ошибка при сохранении сообщения: {e}")
    finally:
        session.close()


def register_usefull_messages_saver_handlers(dp: Dispatcher):
    dp.register_message_handler(
        save_usefull_messages_channel,
        content_types=[ContentType.TEXT],
        chat_id=SUPER_GROUP_ID,
    )
