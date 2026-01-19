import json
import os
import re
from html import escape

from aiogram import types
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from openai import AsyncOpenAI

from config import BASE_DIR, MAX_BOT_MSG_LENGTH, VECTOR_DB_PATH, load_config, logger_bot


# какие теги разрешаем оставить как HTML (Telegram поддерживает subset)
ALLOWED_TAGS = {
    "a", "b", "i", "u", "s", "strong", "em", "code", "pre", "br", "tg-spoiler", "spoiler"
}

_tag_split_re = re.compile(r'(<[^>]*>)')
_tag_name_re = re.compile(r'^<\s*/?\s*([a-zA-Z0-9_-]+)')
_open_a_re = re.compile(r'<a\s+[^>]*>', re.IGNORECASE)
_close_a_re = re.compile(r'</a\s*>', re.IGNORECASE)


def sanitize_and_fix_html(text: str) -> str:
    # 0) Убираем "полуэкранированные" <a ...>, превращаем их в полностью безопасный текст
    text = re.sub(r'&lt;a\s+([^>]*)>', r'&lt;a \1&gt;', text, flags=re.IGNORECASE)

    # 1) нейтрализуем все "неразрешённые" теги
    parts = _tag_split_re.split(text)
    out_parts = []
    for part in parts:
        if not part:
            continue
        if part.startswith('<') and part.endswith('>'):
            m = _tag_name_re.match(part)
            tag_name = m.group(1).lower() if m else None
            if tag_name and tag_name in ALLOWED_TAGS:
                out_parts.append(part)
            else:
                out_parts.append(escape(part))
        else:
            out_parts.append(part)
    safe = ''.join(out_parts)

    # 2) дополняем </a> для незакрытых ссылок
    opens = [(m.start(), m.end()) for m in _open_a_re.finditer(safe)]
    closes = [m.start() for m in _close_a_re.finditer(safe)]
    used_close = [False] * len(closes)
    insert_positions = []

    for o_start, o_end in opens:
        paired = False
        for idx, cpos in enumerate(closes):
            if not used_close[idx] and cpos > o_end:
                used_close[idx] = True
                paired = True
                break
        if not paired:
            next_tag_idx = safe.find('<', o_end)
            insert_at = next_tag_idx if next_tag_idx != -1 else len(safe)
            insert_positions.append(insert_at)

    res = safe
    for pos in sorted(insert_positions, reverse=True):
        res = res[:pos] + '</a>' + res[pos:]

    return res


def split_into_chunks_by_words(text: str, max_len: int):
    if len(text) <= max_len:
        return [text]
    words = text.split(' ')
    chunks = []
    cur = ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_len:
            chunks.append(cur)
            cur = w
        else:
            cur = cur + (' ' if cur else '') + w
    if cur:
        chunks.append(cur)
    return chunks


path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
config = load_config(os.path.join(BASE_DIR, ".env"))

# OpenAI клиент для всех операций
open_ai_token = config.open_ai.token
openai_client = AsyncOpenAI(api_key=open_ai_token)


def semantic_search(query: str, top_k: int = 5, segment: str | None = None):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectordb = FAISS.load_local(VECTOR_DB_PATH, embeddings, allow_dangerous_deserialization=True)

    # Берем все документы по фильтру segment
    flt = {"segment": segment} if segment else None
    results = vectordb.similarity_search(query, k=top_k, filter=flt)
    
    return results


async def kb_query_impl(query: str):
    """Поиск по внутренней базе знаний"""
    logger_bot.info(f"🔍 Ищем ответ в БД Домос. Запрос: '{query}'")
    results = []

    # FAISS-поиск (лекции)
    try:
        docs = semantic_search(query, top_k=3, segment="lectures")
        for doc in docs:
            results.append({
                "text": doc.page_content[:500],
                "score": 0.8,
                "source": "База знаний (лекции)",
                "source_id": "faiss_lectures",
                "is_specific": True
            })
    except Exception as e:
        logger_bot.error(f"❌ Ошибка FAISS lectures: {e}")

    # FAISS-поиск (ЖК)
    try:
        docs = semantic_search(query, top_k=20, segment="real_estate")
        for doc in docs:
            results.append({
                "text": doc.page_content[:500],
                "score": 0.8,
                "source": "База знаний о ЖК",
                "source_id": "faiss_real_estate",
                "is_specific": True
            })
    except Exception as e:
        logger_bot.error(f"❌ Ошибка FAISS real_estate: {e}")

    # FAISS-поиск (Документы)
    try:
        converted_docs_path = os.path.join(path, "converted_docs")
        if os.path.exists(converted_docs_path):
            for filename in os.listdir(converted_docs_path):
                if filename.endswith(".md"):
                    file_path = os.path.join(converted_docs_path, filename)
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if query.lower() in content.lower():
                            results.append({
                                "text": content[:500],
                                "score": 0.7,
                                "source": "База знаний (документы)",
                                "source_id": f"converted_docs_{filename}",
                                "is_specific": True
                            })
    except Exception as e:
        logger_bot.error(f"❌ Ошибка converted_docs: {e}")

    if not results:
        results.append({
            "text": "Общая информация: в базе знаний компании Domosclub содержатся данные о ЖК, ценах и характеристиках квартир.",
            "score": 0.3,
            "source": "База знаний (общая информация)",
            "source_id": "general_info",
            "is_specific": False
        })

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
    
    # Превращаем vector_data в текст для передачи ИИ
    vector_texts = []
    for item in vector_data:
        vector_texts.append(item.get("text", ""))
    vector_text = "\n\n".join(vector_texts)

    # Формируем полный текст запроса для GPT-5
    history_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(history)])
    combined_input = f"""
    Ты — эксперт-консультант по недвижимости в компании Domosclub.

    Правила для ответа:

    1. ВСЕ ссылки в ответе должны быть строго в HTML-формате:
    <a href="URL">Название сайта или описание</a>
    2. НИКАКИХ других форматов ссылок:
    - Никаких Markdown ([текст](URL))
    - Никаких круглых или квадратных скобок вокруг ссылок
    - Никаких raw URLs без <a>
    3. Закрывай все теги корректно. Каждый <a> должен иметь </a>.
    4. Никогда не используй фразы "я не знаю", "обратитесь к специалисту", "информации нет", "я проведу поиск" или "сейчас найду".
    5. Всегда в конце ответа указывай источники информации:
    - Внутренняя база — "База знаний Домос" + ссылка, если есть
    - Результаты поиска — ссылки в HTML-формате
    - Комбинированные ответы — все ссылки в HTML
    6. Не вставляй лишние символы вокруг ссылок (нет скобок, кавычек, точек перед/после, кроме тех, что в HTML-теге).

    Используй историю запросов пользователя только если она релевантна: {history_text}
    Используй информацию из внутренней базы: {vector_text}

    Ответь на запрос пользователя: {user_msg}
    """

    try:
        # Выполняем web_search_preview
        web_response = await openai_client.responses.create(
            model="gpt-5",
            tools=[{
                "type": "web_search_preview",
                "user_location": {
                    "type": "approximate",
                    "country": "RU",
                    "city": "Ekaterinburg",
                    "region": "Ekaterinburg",
                },
                "search_context_size": "low",
            }],
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
    
    if message.text.startswith('/'):
        return
    logger_bot.info(f"Получено сообщение от пользователя {message.from_user.id}")
    logger_bot.info(f"   Текст: '{message.text}'")
        
    wait_msg = await message.reply("⏳ Подождите немного, запрос обрабатывается...")
    logger_bot.info("   💬 Отправляем уведомление пользователю...")
    
    try:
        # Используем новый подход с инструментами
        answer = await run_chat_with_tools(user_id=user_id, user_msg=message.text)
        print(f'{answer=}')
        safe_answer = sanitize_and_fix_html(answer)
        print(f'{safe_answer=}')
        logger_bot.info("   🚀 Запускаем обработку с инструментами...")

        if safe_answer and safe_answer.strip():
            logger_bot.info(f"   ✅ Получен ответ ({len(safe_answer)} символов), отправляем пользователю")

        chunks = split_into_chunks_by_words(safe_answer, MAX_BOT_MSG_LENGTH)
        await wait_msg.edit_text(chunks[0], parse_mode="HTML")
        for c in chunks[1:]:
            await message.answer(c, parse_mode="HTML")

    except Exception as e:
        logger_bot.error(f"   ❌ Ошибка в handle_gpt_message: {e}")
        try:
            # TODO Доделать тут
            ...
        except:
            await wait_msg.edit_text("Извините, произошла ошибка при обработке запроса.")


def register_yandex_gpt(dp):
    dp.register_message_handler(
        handle_gpt_message,
        lambda message: message.chat.type == "private",
        content_types=types.ContentTypes.TEXT,
        state=None
    )
