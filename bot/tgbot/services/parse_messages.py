import os
import platform
import tempfile
import asyncio

import telethon
import sqlite3
from telethon import TelegramClient, events, types, functions
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from openai import AsyncOpenAI

from config import MAIN_DB_PATH, logger_bot, TOPIC_MAP, TOPIC_FIRST_MESSAGES

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


HOST_TURN = os.getenv("HOST_TURN", "False").strip().lower() == "true"

if HOST_TURN:
    CHANNELS = [int(x) for x in os.getenv("PARSE_CHANNELS", "").split(",") if x.strip()]
    SUPER_GROUP_ID = int(os.getenv("SUPER_GROUP_ID", ""))
    api_id = int(os.getenv("TELEGRAM_API_ID", ""))
    api_hash = os.getenv("TELEGRAM_API_HASH")
    session_name = os.getenv("SESSION_NAME", "parse_news_bot")
else:
    CHANNELS = [
        int(x) for x in os.getenv("TEST_PARSE_CHANNELS", "").split(",") if x.strip()
    ]
    SUPER_GROUP_ID = int(os.getenv("TEST_SUPER_GROUP_ID", ""))
    api_id = int(os.getenv("TEST_TELEGRAM_API_ID", ""))
    api_hash = os.getenv("TEST_TELEGRAM_API_HASH")
    session_name = os.getenv("TEST_SESSION_NAME", "test_parse_news_bot")

system_version = platform.uname().release
device_model = platform.uname().machine
app_version = telethon.version.__version__

openai_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENAI_API_KEY"),
)
logger_bot.info("Создаём клиент Telethon")
telethone_client = TelegramClient(
    session_name,
    api_id,
    api_hash,
    system_version=system_version,
    device_model=device_model,
    app_version=app_version,
)

# Словарь для хранения сообщений медиа-групп
# Ключ: grouped_id, Значение: список сообщений
media_groups = {}


async def get_topic_header(theme):
    """Создать заголовок топика или получить существующий"""
    if theme in TOPIC_FIRST_MESSAGES:
        return TOPIC_FIRST_MESSAGES[theme]


def get_adaptive_temperature(q: str) -> float:
    wc = len(q.split())
    return 0.3 if wc <= 6 else 0.4 if wc <= 12 else 0.5


async def is_useful_ai(text):
    # Пример запроса к OpenAI для фильтрации полезных сообщений
    prompt = f"""
    Ты ассистент владельца агентства недвижимости.
    Твоя задача — определить, может ли сообщение быть полезным для бизнеса агентства недвижимости.

    Полезным считается сообщение, если оно связано хотя бы с одной из следующих тем:
    1. Старт продаж — начало продаж объектов, открытие новых ЖК, бронирования.
    2. Обучение — курсы, вебинары, тренинги, мероприятия для риелторов.
    3. Акции — временные предложения, бонусы, промокоды, спецусловия.
    4. Скидки — упоминание скидок, выгодных условий, снижения цены.
    5. Новости — важные новости из сферы недвижимости или законодательства.
    6. Повышенное вознаграждение — бонусы и комиссии для риелторов.
    7. Графики работ — информация о режиме работы офисов, отделов продаж, госслужб.
    8. Способы приобретения — условия ипотеки, рассрочки, субсидии.
    9. Мероприятия — офлайн/онлайн события, презентации, встречи, показы.

    Если сообщение относится хотя бы к одной из этих категорий, ответь **yes**.
    Если не относится или не имеет бизнес-пользы — ответь **no**.

    Сообщение:
    {text}

    Ответь строго одним словом: yes или no.
    """
    response = await openai_client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=8,
        temperature=0,
    )
    answer = response.choices[0].message.content
    logger_bot.info(f"Полезность сообщения: {answer}")
    return answer.startswith("y")


async def get_theme_ai(text) -> str:
    prompt = (
        "Твоя задача — определить основную тему сообщения из списка ниже. "
        "Выбери только одну тему, даже если сообщение подходит под несколько. "
        "Если ни одна тема не подходит — ответь строго 'Неразобранное'.\n\n"
        "Список тем:\n"
        "1. Старт продаж — сообщение о начале продаж объектов, запуске бронирований или открытии нового жилого комплекса.\n"
        "2. Обучение — информация о курсах, тренингах, вебинарах, с указанием даты, места или ссылки на регистрацию.\n"
        "3. Акции — объявления о временных предложениях, бонусах, промокодах, спецусловиях без указания конкретной скидки в процентах.\n"
        "4. Скидки — сообщения, где упоминаются скидки, снижение цен, проценты, выгоды или стоимость ниже обычной.\n"
        "5. Новости — новости из сферы недвижимости, изменения законодательства, новые проекты, решения госорганов.\n"
        "6. Повышенное вознаграждение — предложения с повышенными комиссиями или бонусами для риелторов.\n"
        "7. Графики работ — информация о расписании работы офисов, сотрудников, госслужб, отделов продаж, включая даты и время.\n"
        "8. Способы приобретения — сообщения о новых ипотечных программах, рассрочках, субсидированных ставках, уникальных условиях покупки.\n"
        "9. Мероприятия — офлайн или онлайн события, презентации, встречи, с указанием даты, времени и места.\n\n"
        f"Сообщение:\n{text}\n\n"
        "Ответь одной строкой — только названием темы из списка (без пояснений)."
    )
    response = await openai_client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=32,
        temperature=0,
    )
    theme = str(response.choices[0].message.content)
    return theme


async def send_media_group(files, text, topic_id, theme):
    """Отправляет медиа-группу в указанную тему"""
    try:
        if len(files) == 1:
            # Если один файл, отправляем обычным способом
            await telethone_client.send_file(
                SUPER_GROUP_ID,
                file=files[0],
                caption=text if text else None,
                reply_to=topic_id,
            )
        else:
            # Если несколько файлов, отправляем как альбом
            await telethone_client.send_file(
                SUPER_GROUP_ID,
                file=files,
                caption=text if text else None,
                reply_to=topic_id,
            )
        logger_bot.info(
            f"✅ Отправлена медиа-группа ({len(files)} файлов) в тему '{theme}'"
        )
    except Exception as e:
        logger_bot.error(f"❌ Ошибка при отправке медиа-группы: {e}")
        raise



@telethone_client.on(events.NewMessage(from_users=CHANNELS))
async def handler(event):
    message = event.message
    text = message.text or ""
    media = message.media
    grouped_id = message.grouped_id

    # Если нет текста и медиа — пропускаем
    if not text and not media:
        return

    # Если это часть медиа-группы, сохраняем и планируем обработку
    if grouped_id:
        if grouped_id not in media_groups:
            media_groups[grouped_id] = []
            # Планируем обработку группы через небольшую задержку
            asyncio.create_task(process_media_group_delayed(grouped_id))

        media_groups[grouped_id].append(
            {"message": message, "text": text, "media": media, "event": event}
        )
        return

    # Если это не медиа-группа, обрабатываем сразу
    await process_message(message, text, media, event)


async def process_media_group_delayed(grouped_id):
    """Обрабатывает медиа-группу после небольшой задержки"""
    # Ждём 2 секунды, чтобы собрать все сообщения группы
    await asyncio.sleep(2)

    if grouped_id in media_groups:
        messages_list = media_groups[grouped_id]
        if messages_list:
            # Берём первое сообщение для получения event
            first_event = messages_list[0]["event"]
            await process_message(grouped_id=grouped_id, event=first_event)


async def process_message(
    message=None, text=None, media=None, event=None, grouped_id=None
):
    """Обрабатывает одно сообщение или медиа-группу"""
    # Если передан grouped_id, значит это обработка медиа-группы
    if grouped_id is None:
        if message is None:
            return
        grouped_id = message.grouped_id

    # Если это медиа-группа, обрабатываем все сообщения вместе
    if grouped_id and grouped_id in media_groups:
        messages_list = media_groups[grouped_id]

        # Собираем весь текст из всех сообщений группы
        full_text = ""
        for msg_data in messages_list:
            msg_text = msg_data["text"]
            if msg_text:
                if full_text:
                    full_text += "\n\n" + msg_text
                else:
                    full_text = msg_text

        # Используем текст из первого сообщения для проверки
        check_text = full_text if full_text else messages_list[0]["text"]

        # Проверяем полезность через AI
        logger_bot.info(f"Проверяем медиа-группу на полезность: {check_text[:100]}")
        if not await is_useful_ai(check_text):
            # Удаляем группу из словаря
            del media_groups[grouped_id]
            return

        # Определяем тему сообщения
        theme = await get_theme_ai(check_text)
        logger_bot.info(f"Нашли полезную медиа-группу с темой: {theme}")

        thread_id = TOPIC_MAP.get(theme)
        if not thread_id:
            logger_bot.error(
                f"Тема '{theme}' не найдена в topic_map, медиа-группа не переслана."
            )
            del media_groups[grouped_id]
            return

        topic_id = await get_topic_header(theme)

        # Добавляем источник в сообщение
        chat = await event.get_chat()
        if getattr(chat, "username", None):
            channel_link = f"https://t.me/{chat.username}"
        else:
            channel_link = None
        full_text = (
            f"Источник: {chat.title}\n{channel_link}\n\n{full_text}"
            if full_text
            else f"Источник: {chat.title}\n{channel_link}"
        )

        # Скачиваем все файлы
        files = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for msg_data in messages_list:
                msg_media = msg_data["media"]
                if isinstance(msg_media, (MessageMediaPhoto, MessageMediaDocument)):
                    file_path = await msg_data["message"].download_media(file=tmpdir)
                    if file_path and os.path.exists(file_path):
                        files.append(file_path)
                        logger_bot.info(f"📥 Файл скачан: {file_path}")

            if files:
                # Отправляем медиа-группу в основную тему
                await send_media_group(files, full_text, topic_id, theme)

                # Если тема "Акции", отправляем также в "Контент"
                if theme == "Акции":
                    content_thread_id = TOPIC_MAP.get("Контент")
                    content_topic_id = await get_topic_header("Контент")
                    if content_thread_id and content_topic_id:
                        logger_bot.info("📋 Дублируем сообщение из 'Акции' в 'Контент'")
                        await send_media_group(
                            files, full_text, content_topic_id, "Контент"
                        )
            else:
                # Если не удалось скачать файлы, отправляем только текст
                logger_bot.warning(
                    "⚠️ Не удалось скачать файлы, отправляем только текст"
                )
                await telethone_client.send_message(
                    SUPER_GROUP_ID,
                    full_text,
                    reply_to=topic_id,
                )

                if theme == "Акции":
                    content_topic_id = await get_topic_header("Контент")
                    if content_topic_id:
                        await telethone_client.send_message(
                            SUPER_GROUP_ID,
                            full_text,
                            reply_to=content_topic_id,
                        )

        # Удаляем группу из словаря
        del media_groups[grouped_id]
        return

    # Обработка одиночного сообщения
    # Проверяем полезность через AI
    logger_bot.info(f"Проверяем новое сообщение на полезность: {text[:100]}")
    if not await is_useful_ai(text):
        return

    # Определяем тему сообщения
    theme = await get_theme_ai(text)
    logger_bot.info(f"Нашли полезное сообщение с темой: {theme}")

    thread_id = TOPIC_MAP.get(theme)
    if not thread_id:
        logger_bot.error(
            f"Тема '{theme}' не найдена в topic_map, сообщение не переслано."
        )
        return

    topic_id = await get_topic_header(theme)

    # Добавляем источник в сообщение
    chat = await event.get_chat()
    if getattr(chat, "username", None):
        channel_link = f"https://t.me/{chat.username}"
    else:
        channel_link = None
    text = f"Источник: {chat.title}\n{channel_link}\n\n{text}"

    try:
        if isinstance(media, (MessageMediaPhoto, MessageMediaDocument)):
            # Скачиваем файл во временную директорию
            with tempfile.TemporaryDirectory() as tmpdir:
                file_path = await message.download_media(file=tmpdir)
                if file_path and os.path.exists(file_path):
                    logger_bot.info(f"📥 Файл скачан: {file_path}")

                    # Отправляем файл в группу
                    await telethone_client.send_file(
                        SUPER_GROUP_ID,
                        file=file_path,
                        caption=text if text else None,
                        reply_to=topic_id,
                    )

                    logger_bot.info(f"📤 Файл отправлен и будет удалён: {file_path}")

                    # Если тема "Акции", отправляем также в "Контент"
                    if theme == "Акции":
                        content_topic_id = await get_topic_header("Контент")
                        if content_topic_id:
                            logger_bot.info(
                                "📋 Дублируем сообщение из 'Акции' в 'Контент'"
                            )
                            await telethone_client.send_file(
                                SUPER_GROUP_ID,
                                file=file_path,
                                caption=text if text else None,
                                reply_to=content_topic_id,
                            )
                else:
                    logger_bot.warning(
                        "⚠️ Не удалось скачать файл, отправляем только текст"
                    )
                    await telethone_client.send_message(
                        SUPER_GROUP_ID,
                        text,
                        reply_to=topic_id,
                    )

                    if theme == "Акции":
                        content_topic_id = await get_topic_header("Контент")
                        if content_topic_id:
                            await telethone_client.send_message(
                                SUPER_GROUP_ID,
                                text,
                                reply_to=content_topic_id,
                            )
        else:
            # Если это просто текст (или web preview)
            await telethone_client.send_message(
                SUPER_GROUP_ID,
                text,
                reply_to=topic_id,
            )

            # Если тема "Акции", отправляем также в "Контент"
            if theme == "Акции":
                content_topic_id = await get_topic_header("Контент")
                if content_topic_id:
                    logger_bot.info("📋 Дублируем сообщение из 'Акции' в 'Контент'")
                    await telethone_client.send_message(
                        SUPER_GROUP_ID,
                        text,
                        reply_to=content_topic_id,
                    )

        logger_bot.info(
            f"✅ Переслано сообщение в тему '{theme}' "
            f"(thread_id={thread_id}, topic_id={topic_id}): {text[:100]}"
        )

    except Exception as e:
        logger_bot.error(f"❌ Ошибка при отправке в группу: {e}")


CHECK_INTERVAL = 60  # проверка каждые 60 секунд


async def get_users_all_paid_users(pay_status):
    """Получаем user_id по статусу оплаты"""
    try:
        conn = sqlite3.connect(MAIN_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT fullName FROM users WHERE pay_status = ?",
            (pay_status,),
        )
        users = {row[0] for row in cursor.fetchall()}
        conn.close()
        return users
    except Exception as e:
        logger_bot.error(
            f"Ошибка получения пользователей с pay_status {pay_status}: {e}"
        )
        return set()


async def sync_users_to_supergroup():
    while True:
        try:
            # 1. Получаем список всех пользователей из get_all_users()
            all_users = await get_users_all_paid_users("1")
            logger_bot.info(f"{all_users=}")

            # 2. Получаем текущих участников супер-группы
            participants = await telethone_client.get_participants(SUPER_GROUP_ID)

            existing_usernames = {p.username for p in participants if p.username}
            logger_bot.info(f"{existing_usernames=}")

            # 3. Фильтруем пользователей, которых нет в группе
            to_add = [
                username for username in all_users if username not in existing_usernames
            ]
            logger_bot.info(f'{to_add=}')

            for username in to_add:
                try:
                    # Получаем entity пользователя по username
                    entity = await telethone_client.get_input_entity(username)
                    await telethone_client(
                        InviteToChannelRequest(channel=SUPER_GROUP_ID, users=[entity])
                    )
                    logger_bot.info(
                        f"✅ Пользователь {username} добавлен в супер-группу"
                    )
                    await asyncio.sleep(CHECK_INTERVAL)
                except Exception as e:
                    logger_bot.error(f"❌ Не удалось добавить {username}: {e}")

        except Exception as e:
            logger_bot.error(f"Ошибка синхронизации пользователей: {e}")

        await asyncio.sleep(36000)


def main():
    with telethone_client:
        # Запускаем фоновую синхронизацию пользователей
        telethone_client.loop.create_task(sync_users_to_supergroup())

        telethone_client.run_until_disconnected()


main()
