import os

from aiogram import Dispatcher, types

from config import logger_bot

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


HOST_TURN = os.getenv("HOST_TURN", "False").strip().lower() == "true"

if HOST_TURN:
    TARGET_CHAT_ID = int(os.getenv("SUPER_GROUP_ID", ""))
else:
    TARGET_CHAT_ID = int(os.getenv("TEST_SUPER_GROUP_ID", ""))


async def join_request_handler(request: types.ChatJoinRequest):
    """
    Обрабатывает входящие заявки в группу.
    Работает только для конкретной супергруппы.
    """

    chat_id = request.chat.id
    user = request.from_user

    if chat_id != TARGET_CHAT_ID:
        # Игнорируем чужие чаты
        return

    logger_bot.info(f"Новая заявка: user={user.id}, chat={chat_id}")

    # Принять заявку
    await request.approve()

    # Можно отправить пользователю сообщение
    try:
        await request.bot.send_message(
            user.id, "Ваша заявка одобрена. Добро пожаловать!"
        )
    except Exception as e:
        logger_bot.error(f"Ошибка при добавлении пользователя в супергруппу: {e}")


def register_chat_join_requests(dp: Dispatcher):
    """
    Регистрируем обработчик в диспетчере, как вы делаете в других файлах.
    """

    dp.register_chat_join_request_handler(join_request_handler)
