import os
from datetime import datetime
from typing import Optional

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.tgbot.databases.database import DatabaseConnection
from config import MAIN_DB_PATH, logger_bot, DB_TYPE, load_config

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Получаем ID группы поддержки из переменных окружения
HOST_TURN = os.getenv("HOST_TURN", "False").strip().lower() == "true"
if HOST_TURN:
    # support_group_id_str = os.getenv("SUPPORT_GROUP_ID", "")
    support_group_id_str = '-1003794590514'
    SUPPORT_GROUP_ID = int(support_group_id_str) if support_group_id_str else None
else:
    support_group_id_str = os.getenv("TEST_SUPPORT_GROUP_ID", "")
    SUPPORT_GROUP_ID = int(support_group_id_str) if support_group_id_str else None


class SupportStates(StatesGroup):
    """Состояния для техподдержки"""
    waiting_message = State()
    waiting_reply = State()


def init_support_table():
    """Инициализация таблицы техподдержки"""
    db = DatabaseConnection(MAIN_DB_PATH, schema="bot" if DB_TYPE == "postgres" else None)
    
    if DB_TYPE == "postgres":
        # PostgreSQL
        query = """
        CREATE TABLE IF NOT EXISTS bot.support_messages (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            username VARCHAR(255),
            full_name VARCHAR(255),
            message_text TEXT NOT NULL,
            group_message_id INTEGER,
            reply_to_message_id INTEGER,
            status VARCHAR(50) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_support_user_id ON bot.support_messages(user_id);
        CREATE INDEX IF NOT EXISTS idx_support_group_message_id ON bot.support_messages(group_message_id);
        CREATE INDEX IF NOT EXISTS idx_support_status ON bot.support_messages(status);
        """
    else:
        # SQLite
        query = """
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            full_name TEXT,
            message_text TEXT NOT NULL,
            group_message_id INTEGER,
            reply_to_message_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_support_user_id ON support_messages(user_id);
        CREATE INDEX IF NOT EXISTS idx_support_group_message_id ON support_messages(group_message_id);
        CREATE INDEX IF NOT EXISTS idx_support_status ON support_messages(status);
        """
    
    try:
        db.execute(query)
        logger_bot.info("✅ Таблица support_messages успешно создана/проверена")
    except Exception as e:
        logger_bot.error(f"❌ Ошибка при создании таблицы support_messages: {e}")


def save_support_message(
    user_id: int,
    username: Optional[str],
    full_name: Optional[str],
    message_text: str,
    group_message_id: Optional[int] = None,
    reply_to_message_id: Optional[int] = None,
    status: str = "pending"
) -> Optional[int]:
    """Сохраняет сообщение техподдержки в БД"""
    db = DatabaseConnection(MAIN_DB_PATH, schema="bot" if DB_TYPE == "postgres" else None)
    
    if DB_TYPE == "postgres":
        query = """
        INSERT INTO bot.support_messages 
        (user_id, username, full_name, message_text, group_message_id, reply_to_message_id, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        RETURNING id
        """
    else:
        query = """
        INSERT INTO support_messages 
        (user_id, username, full_name, message_text, group_message_id, reply_to_message_id, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """
    
    try:
        if DB_TYPE == "postgres":
            result = db.execute(query, (user_id, username, full_name, message_text, group_message_id, reply_to_message_id, status))
            if result and len(result) > 0:
                return result[0]['id']
        else:
            db.execute(query, (user_id, username, full_name, message_text, group_message_id, reply_to_message_id, status))
            # Получаем последний вставленный ID
            result = db.fetchone("SELECT last_insert_rowid() as id")
            if result:
                return result[0] if isinstance(result, tuple) else result.get('id')
        return None
    except Exception as e:
        logger_bot.error(f"❌ Ошибка при сохранении сообщения техподдержки: {e}")
        return None


def get_support_message_by_group_id(group_message_id: int) -> Optional[dict]:
    """Получает сообщение техподдержки по ID сообщения в группе"""
    db = DatabaseConnection(MAIN_DB_PATH, schema="bot" if DB_TYPE == "postgres" else None)
    
    if DB_TYPE == "postgres":
        query = "SELECT * FROM bot.support_messages WHERE group_message_id = %s LIMIT 1"
    else:
        query = "SELECT * FROM support_messages WHERE group_message_id = ? LIMIT 1"
    
    try:
        result = db.fetchone(query, (group_message_id,))
        if result:
            if isinstance(result, tuple):
                # SQLite возвращает tuple, преобразуем в dict
                columns = ['id', 'user_id', 'username', 'full_name', 'message_text', 
                          'group_message_id', 'reply_to_message_id', 'status', 'created_at', 'updated_at']
                return dict(zip(columns, result))
            return result
        return None
    except Exception as e:
        logger_bot.error(f"❌ Ошибка при получении сообщения техподдержки: {e}")
        return None


def update_support_message_status(message_id: int, status: str):
    """Обновляет статус сообщения техподдержки"""
    db = DatabaseConnection(MAIN_DB_PATH, schema="bot" if DB_TYPE == "postgres" else None)
    
    if DB_TYPE == "postgres":
        query = """
        UPDATE bot.support_messages 
        SET status = %s, updated_at = NOW() 
        WHERE id = %s
        """
    else:
        query = """
        UPDATE support_messages 
        SET status = ?, updated_at = datetime('now') 
        WHERE id = ?
        """
    
    try:
        db.execute(query, (status, message_id))
    except Exception as e:
        logger_bot.error(f"❌ Ошибка при обновлении статуса сообщения: {e}")


async def start_support_chat(callback: CallbackQuery, state: FSMContext):
    """Начало диалога с техподдержкой"""
    await SupportStates.waiting_message.set()
    await callback.message.answer(
        "💬 Напишите ваш вопрос или опишите проблему, и мы обязательно вам поможем!"
    )
    await callback.answer()


async def handle_support_message(message: Message, state: FSMContext):
    """Обработка сообщения от пользователя и отправка в группу поддержки"""
    if SUPPORT_GROUP_ID is None:
        await message.answer(
            "❌ Группа поддержки не настроена. Обратитесь к администратору."
        )
        await state.finish()
        return
    
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name or message.from_user.first_name
    
    # Получаем текст сообщения
    if message.text:
        message_text = message.text
    elif message.caption:
        message_text = message.caption
    else:
        message_text = "[Медиа-файл]"
    
    # Формируем сообщение для группы
    group_message_text = (
        f"📨 <b>Новое обращение в техподдержку</b>\n\n"
        f"👤 <b>Пользователь:</b> {full_name}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
    )
    
    if username:
        group_message_text += f"📱 <b>Username:</b> @{username}\n"
    
    group_message_text += f"\n💬 <b>Сообщение:</b>\n{message_text}"
    
    try:
        # Отправляем сообщение в группу поддержки
        if message.photo:
            # Если есть фото, отправляем с фото
            sent_message = await message.bot.send_photo(
                chat_id=SUPPORT_GROUP_ID,
                photo=message.photo[-1].file_id,
                caption=group_message_text,
                parse_mode="HTML"
            )
        elif message.document:
            # Если есть документ
            sent_message = await message.bot.send_document(
                chat_id=SUPPORT_GROUP_ID,
                document=message.document.file_id,
                caption=group_message_text,
                parse_mode="HTML"
            )
        elif message.video:
            # Если есть видео
            sent_message = await message.bot.send_video(
                chat_id=SUPPORT_GROUP_ID,
                video=message.video.file_id,
                caption=group_message_text,
                parse_mode="HTML"
            )
        elif message.voice:
            # Если есть голосовое сообщение
            sent_message = await message.bot.send_voice(
                chat_id=SUPPORT_GROUP_ID,
                voice=message.voice.file_id,
                caption=group_message_text,
                parse_mode="HTML"
            )
        else:
            # Обычное текстовое сообщение
            sent_message = await message.bot.send_message(
                chat_id=SUPPORT_GROUP_ID,
                text=group_message_text,
                parse_mode="HTML"
            )
        
        # Сохраняем сообщение в БД
        support_id = save_support_message(
            user_id=user_id,
            username=username,
            full_name=full_name,
            message_text=message_text,
            group_message_id=sent_message.message_id,
            status="pending"
        )
        
        if support_id:
            logger_bot.info(f"✅ Сообщение техподдержки сохранено с ID: {support_id}")
        
        await message.answer(
            "✅ Ваше сообщение отправлено в техподдержку. Мы ответим вам в ближайшее время!"
        )
        await state.finish()
        
    except Exception as e:
        logger_bot.error(f"❌ Ошибка при отправке сообщения в группу поддержки: {e}")
        await message.answer(
            "❌ Произошла ошибка при отправке сообщения. Попробуйте позже."
        )
        await state.finish()


async def handle_group_reply(message: Message):
    """Обработка ответа на сообщение в группе поддержки"""
    # Проверяем, что группа поддержки настроена
    if SUPPORT_GROUP_ID is None:
        return
    
    # Проверяем, что сообщение находится в группе поддержки
    if message.chat.id != SUPPORT_GROUP_ID:
        return
    
    # Проверяем, что это ответ на сообщение
    if not message.reply_to_message:
        return
    
    # Проверяем, что отвечающий является администратором группы или бота
    try:
        # Получаем информацию о пользователе в группе
        chat_member = await message.bot.get_chat_member(
            chat_id=SUPPORT_GROUP_ID,
            user_id=message.from_user.id
        )
        
        # Проверяем, является ли пользователь администратором или создателем группы
        if chat_member.status not in ['creator', 'administrator']:
            # Также проверяем, является ли пользователь админом бота
            config = load_config()
            if message.from_user.id not in config.tg_bot.admin_ids:
                logger_bot.warning(
                    f"⚠️ Пользователь {message.from_user.id} попытался ответить, но не является админом"
                )
                return
    except Exception as e:
        logger_bot.error(f"❌ Ошибка при проверке прав администратора: {e}")
        # В случае ошибки проверяем только список админов бота
        config = load_config()
        if message.from_user.id not in config.tg_bot.admin_ids:
            return
    
    # Получаем ID сообщения, на которое отвечают
    replied_message_id = message.reply_to_message.message_id
    
    # Ищем исходное сообщение в БД
    support_message = get_support_message_by_group_id(replied_message_id)
    
    if not support_message:
        logger_bot.warning(f"⚠️ Не найдено сообщение техподдержки с group_message_id={replied_message_id}")
        return
    
    user_id = support_message['user_id']
    username = support_message.get('username')
    full_name = support_message.get('full_name', 'Пользователь')
    
    # Получаем текст ответа
    if message.text:
        reply_text = message.text
    elif message.caption:
        reply_text = message.caption
    else:
        reply_text = "[Медиа-файл]"
    
    # Формируем сообщение для пользователя
    user_message_text = (
        f"💬 <b>Ответ от техподдержки:</b>\n\n{reply_text}\n\n"
        f"📝 <i>Ваш вопрос:</i> {support_message['message_text'][:100]}..."
    )
    
    try:
        # Отправляем ответ пользователю
        if message.photo:
            await message.bot.send_photo(
                chat_id=user_id,
                photo=message.photo[-1].file_id,
                caption=user_message_text,
                parse_mode="HTML"
            )
        elif message.document:
            await message.bot.send_document(
                chat_id=user_id,
                document=message.document.file_id,
                caption=user_message_text,
                parse_mode="HTML"
            )
        elif message.video:
            await message.bot.send_video(
                chat_id=user_id,
                video=message.video.file_id,
                caption=user_message_text,
                parse_mode="HTML"
            )
        elif message.voice:
            await message.bot.send_voice(
                chat_id=user_id,
                voice=message.voice.file_id,
                caption=user_message_text,
                parse_mode="HTML"
            )
        else:
            await message.bot.send_message(
                chat_id=user_id,
                text=user_message_text,
                parse_mode="HTML"
            )
        
        # Обновляем статус сообщения
        update_support_message_status(support_message['id'], "answered")
        
        # Сохраняем ответ в БД
        save_support_message(
            user_id=user_id,
            username=username,
            full_name=full_name,
            message_text=reply_text,
            reply_to_message_id=replied_message_id,
            status="answered"
        )
        
        logger_bot.info(f"✅ Ответ отправлен пользователю {user_id} (ID сообщения: {support_message['id']})")
        
    except Exception as e:
        logger_bot.error(f"❌ Ошибка при отправке ответа пользователю: {e}")
        # Пытаемся отправить уведомление в группу
        try:
            await message.reply(
                f"❌ Не удалось отправить ответ пользователю. Ошибка: {str(e)}"
            )
        except:
            pass


def register_support_chat_handlers(dp: Dispatcher):
    """Регистрация хендлеров техподдержки"""
    # Проверяем, что группа поддержки настроена
    if SUPPORT_GROUP_ID is None:
        logger_bot.warning(
            "⚠️ SUPPORT_GROUP_ID не установлен. Хендлеры техподдержки не будут работать. "
            "Установите SUPPORT_GROUP_ID или TEST_SUPPORT_GROUP_ID в переменных окружения."
        )
        return
    
    # Инициализируем таблицу при регистрации
    init_support_table()
    
    # Хендлер для начала диалога с техподдержкой (через callback)
    dp.register_callback_query_handler(
        start_support_chat,
        lambda c: c.data == "support_chat",
        state="*"
    )
    
    # Хендлер для обработки сообщений от пользователей
    dp.register_message_handler(
        handle_support_message,
        state=SupportStates.waiting_message,
        content_types=['text', 'photo', 'document', 'video', 'voice']
    )
    
    # Хендлер для обработки ответов в группе поддержки
    # Проверка chat_id выполняется внутри функции handle_group_reply
    dp.register_message_handler(
        handle_group_reply,
        content_types=['text', 'photo', 'document', 'video', 'voice']
    )

