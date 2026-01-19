import json
import os
import re
from html import unescape

from aiogram import types
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from openai import AsyncOpenAI

from bot.tgbot.databases.pay_db import getBannedUserId, getUserPay
from config import BASE_DIR, MAX_BOT_MSG_LENGTH, VECTOR_DB_PATH, load_config, logger_bot
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


# какие теги разрешаем оставить как HTML (Telegram поддерживает subset)
ALLOWED_TAGS = {
    "a",
    "b",
    "i",
    "u",
    "s",
    "strong",
    "em",
    "code",
    "pre",
    "br",
    "tg-spoiler",
    "spoiler",
}

_tag_split_re = re.compile(r"(<[^>]*>)")
_tag_name_re = re.compile(r"^<\s*/?\s*([a-zA-Z0-9_-]+)")
_open_a_re = re.compile(r"<a\s+[^>]*>", re.IGNORECASE)
_close_a_re = re.compile(r"</a\s*>", re.IGNORECASE)


# ---------------------------------------------------------
#  URL UTILITIES — ЯВНОЕ РАСПОЗНАВАНИЕ ССЫЛОК ДЛЯ GPT
# ---------------------------------------------------------

_url_re = re.compile(r"(https?://[^\s<]+)")


def extract_urls(text: str) -> list[str]:
    """Извлечь URL корректно, не повреждая HTML."""
    return _url_re.findall(text)


def inject_markdown_links(text: str) -> str:
    """
    Преобразует URL -> [URL](URL)
    Это гарантирует, что любая LLM, включая GPT-5, трактует URL как ссылку.
    """
    return _url_re.sub(r"[\1](\1)", text)


def strip_all_tags(text: str) -> str:
    # Заменяем <...> на только содержимое внутри href или текста
    # 1. если есть href="..." → оставляем только саму ссылку
    text = re.sub(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>', r"\1 ", text)

    # 2. убираем вообще все остальные теги целиком (<b>, </a>, <i> и любые)
    text = re.sub(r"<[^>]+>", "", text)

    # 3. Чистим html-сущности (&lt; → < и т.п.)
    text = unescape(text)

    # 4. Убираем лишние пробелы
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n\s*", "\n", text)

    return text.strip()


def split_into_chunks_by_words(text: str, max_len: int):
    if len(text) <= max_len:
        return [text]
    words = text.split(" ")
    chunks = []
    cur = ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_len:
            chunks.append(cur)
            cur = w
        else:
            cur = cur + (" " if cur else "") + w
    if cur:
        chunks.append(cur)
    return chunks


path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
config = load_config(os.path.join(BASE_DIR, ".env"))

# OpenAI клиент для всех операций
openai_client = AsyncOpenAI(
    base_url=os.getenv("OPENAI_API_BASE"),
    api_key=config.open_ai.token,
)


def semantic_search(query: str, top_k: int = 5, segment: str | None = None):
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_EMBEDDING_KEY", ""),
        base_url=os.getenv("OPENAI_API_EMBEDDING_BASE"),
    )
    vectordb = FAISS.load_local(
        VECTOR_DB_PATH, embeddings, allow_dangerous_deserialization=True
    )

    # Берем все документы по фильтру segment
    flt = {"segment": segment} if segment else None
    results = vectordb.similarity_search(query, k=top_k, filter=flt)

    return results


async def kb_query_impl(query: str):
    """Поиск по внутренней базе знаний"""
    logger_bot.info(f"🔍 Ищем ответ в векторной базе. Запрос: '{query}'")
    results = []

    # FAISS-поиск (лекции)
    try:
        docs = semantic_search(query, top_k=3, segment="lectures")
        for doc in docs:
            results.append(
                {
                    "text": doc.page_content[:500],
                    "score": 0.8,
                    "source": "Информация с канала DOMOS Club",
                    "source_id": "faiss_lectures",
                    "is_specific": True,
                }
            )
    except Exception as e:
        logger_bot.error(f"❌ Ошибка FAISS lectures: {e}")

    # FAISS-поиск (ЖК)
    try:
        docs = semantic_search(query, top_k=20, segment="real_estate")
        for doc in docs:
            results.append(
                {
                    "text": doc.page_content[:500],
                    "score": 0.8,
                    "source": "База знаний ЖК (сайты nmarket и trendagent)",
                    "source_id": "faiss_real_estate",
                    "is_specific": True,
                }
            )
    except Exception as e:
        logger_bot.error(f"❌ Ошибка FAISS real_estate: {e}")

    # # FAISS-поиск (Документы)
    # try:
    #     converted_docs_path = os.path.join(path, "converted_docs")
    #     if os.path.exists(converted_docs_path):
    #         for filename in os.listdir(converted_docs_path):
    #             if filename.endswith(".md"):
    #                 file_path = os.path.join(converted_docs_path, filename)
    #                 with open(file_path, "r", encoding="utf-8") as f:
    #                     content = f.read()
    #                     if query.lower() in content.lower():
    #                         results.append({
    #                             "text": content[:500],
    #                             "score": 0.7,
    #                             "source": "База знаний (документы)",
    #                             "source_id": f"converted_docs_{filename}",
    #                             "is_specific": True
    #                         })
    # except Exception as e:
    #     logger_bot.error(f"❌ Ошибка converted_docs: {e}")

    if not results:
        results.append(
            {
                "text": "Общая информация: в базе знаний компании Domosclub содержатся данные о ЖК, ценах и характеристиках квартир.",
                "score": 0.3,
                "source": "База знаний (общая информация)",
                "source_id": "general_info",
                "is_specific": False,
            }
        )

    return json.dumps(results[:10], ensure_ascii=False)


user_histories: dict[int, list[str]] = {}


async def run_chat_with_tools(user_id: int, user_msg: str, max_history: int = 3):
    """
    Простой обработчик:
    - Делает web_search_preview через GPT-5
    - Возвращает текстовый ответ пользователю
    """
    global user_histories

    def extract_text(resp):
        """Универсальный парсер ответа под GPT-5 и GPT-4.1"""
        if hasattr(resp, "output_text") and resp.output_text:
            return resp.output_text.strip()
        if hasattr(resp, "choices") and resp.choices:
            msg = getattr(resp.choices[0], "message", None)
            if msg and getattr(msg, "content", None):
                return msg.content.strip()
        return ""

    # Обновляем историю пользователя
    history = user_histories.get(user_id, [])
    history.append(user_msg)
    if len(history) > max_history:
        history = history[-max_history:]  # оставляем последние N
    user_histories[user_id] = history  # сохраняем обратно

    # Получаем данные из векторной базы
    vector_response = await kb_query_impl(user_msg)
    vector_data = json.loads(vector_response)
    sources = [item["source"] for item in vector_data]

    # Превращаем vector_data в текст для передачи ИИ
    vector_texts = []
    for item in vector_data:
        vector_texts.append(item.get("text", ""))
    vector_text = "\n\n".join(vector_texts)

    # Формируем полный текст запроса для GPT-5
    history_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(history)])
    combined_input = f"""
    Ты — эксперт-консультант по недвижимости в компании Domosclub.
    Ограничение поиска:
    • Разрешено использовать данные ТОЛЬКО с сайтов:
        - https://avito.ru
        - https://cian.ru
        - https://domclick.ru

    Если инструмент поиска выдаёт ссылки с других сайтов – игнорируй их и НЕ используй в ответе.

    Правила для ответа:
    1. Никогда не используй фразы "я не знаю", "обратитесь к специалисту", "информации нет", "я проведу поиск" или "сейчас найду".
    2. Всегда в конце ответа указывай источники информации:
        - Внутренняя база — Для указания источников используй {' '.join(sources)}. Повторяющиеся источники используй 1 раз.
        - Результаты поиска — ссылки в HTML-формате.
        - Комбинированные ответы — все ссылки в HTML.

    Используй историю запросов пользователя только если она релевантна: {history_text}
    Используй информацию из внутренней базы: {vector_text}

    ========================================================
    ПРАВИЛА ОБРАБОТКИ ССЫЛОК:

    1. Любая строка, начинающаяся с http:// или https://, всегда является ссылкой.
    2. Если в запросе встречается URL, он всегда должен интерпретироваться как гиперссылка.
    3. URL, не оформленные тегом <a>, автоматически трактуй как полноценные ссылки.
    4. Если URL находится в Markdown-формате [URL](URL) — считай его кликабельной гиперссылкой.
    5. Никогда не изменяй структуру URL и не разрывай ссылки на части.
    6. В ответе всегда сохраняй URL в исходном виде или в HTML (<a href="URL">URL</a>).
    ========================================================

    Ответь на запрос пользователя: {user_msg}
    """

    try:
        # Выполняем web_search_preview
        web_response = await openai_client.responses.create(
            model="openai/gpt-5",
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {
                        "type": "approximate",
                        "country": "RU",
                        "city": "Ekaterinburg",
                        "region": "Ekaterinburg",
                    },
                    "search_context_size": "low",
                }
            ],
            input=combined_input,
        )

        text = extract_text(web_response)
        final_answer = text or "Извините, не удалось получить ответ."
        return final_answer

    except Exception as e:
        logger_bot.error(f"❌ Ошибка в run_chat_with_tools: {e}")
        return "Извините, произошла ошибка при обработке запроса."


async def handle_gpt_message(message: types.Message):
    user_id = message.from_user.id
    banned = getBannedUserId(user_id)

    if banned != 0:
        await message.answer(
            "⭕  Ваш аккаунт забанен, обратитесь к администрации бота!"
        )
        return

    payed = getUserPay(user_id)
    if payed != 1:
        await message.answer("⭕ Сначала оплатите подписку!")
        return

    if message.text.startswith("/"):
        return

    logger_bot.info(f"Получено сообщение от пользователя {user_id}")
    logger_bot.info(f"   Текст: '{message.text}'")

    original_user_msg = message.text
    user_msg_normalized = inject_markdown_links(original_user_msg)

    wait_msg = await message.reply("⏳ Подождите немного, запрос обрабатывается...")
    logger_bot.info("   💬 Уведомили пользователя о старте обработки...")

    answer = None  # 🔴 КРИТИЧЕСКИ ВАЖНО

    try:
        logger_bot.info("   🚀 Запускаем обработку с инструментами...")
        answer = await run_chat_with_tools(
            user_id=user_id, user_msg=user_msg_normalized
        )

        if not answer or not answer.strip():
            raise ValueError("Пустой ответ от GPT")

        chunks = split_into_chunks_by_words(answer, MAX_BOT_MSG_LENGTH)
        await wait_msg.edit_text(chunks[0], parse_mode="HTML")
        for c in chunks[1:]:
            await message.answer(c, parse_mode="HTML")

    except Exception as e:
        logger_bot.error(f"❌ Ошибка при обработке ответа: {e}")

        # если answer уже есть — пробуем очистить HTML
        if answer:
            try:
                logger_bot.info("Пробуем удалить HTML-теги")
                safe_answer = strip_all_tags(answer)
                new_chunks = split_into_chunks_by_words(
                    safe_answer, MAX_BOT_MSG_LENGTH
                )
                await wait_msg.edit_text(new_chunks[0])
                for c in new_chunks[1:]:
                    await message.answer(c)
                return
            except Exception as e2:
                logger_bot.error(f"❌ Ошибка при очистке HTML: {e2}")

        await wait_msg.edit_text(
            "Извините, произошла ошибка при обработке запроса."
        )

def register_yandex_gpt(dp):
    dp.register_message_handler(
        handle_gpt_message,
        lambda message: message.chat.type == "private",
        content_types=types.ContentTypes.TEXT,
        state=None,
    )
