import os
import sqlite3

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from openai import AsyncOpenAI

from bot.tgbot.keyboards.inline import mainmenu_btn, mainmenu_mk, request_from_db_keyboard
from bot.tgbot.databases.pay_db import getBannedUserId, changeUsername, checkUserExists, regUser

# Загрузка переменных окружения
from dotenv import load_dotenv
load_dotenv()


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH_FLOORS = os.path.join(BASE_DIR, "databases", "nmarket.db")
DB_PATH_AUDIO = os.path.join(BASE_DIR, "databases", "downloaded_audio.db")
INDEX_DIR = os.path.join(BASE_DIR, "vector_index")

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def parse_request_floor_with_gpt(user_input: str):
    prompt = """
Ты — парсер пользовательских запросов по недвижимости.
ВЕРНИ РОВНО ОДИН JSON-ОБЪЕКТ (без каких-либо пояснений, объяснений, дополнительных слов и без обратных кавычек).
Если параметр не указан — поставь null. Числа возвращай как числа (не строки). Булевы значения — true/false (JSON).

Структура результата (ключи — строго такие же, не добавляй новые ключи):

{
  "complex_filters": {
    "url": null,
    "name": null,
    "address": null,
    "developer": null,
    "floor_count": { "min": null, "max": null },
    "status": null,
    "key_issue": null,
    "parking": null,
    "ceiling_height": { "min": null, "max": null },
    "finishing": null,
    "contract_type": null,
    "building_type": null,
    "registration": null,
    "payment_options": null,
    "units_total": { "min": null, "max": null },
    "description": null,
    "contact_name": null,
    "contact_phone": null,
    "contact_email": null
  },
  "unit_filters": {
    "complex_id": null,
    "unit_type": null,
    "building": null,
    "section": null,
    "floor": { "min": null, "max": null },        /* маппится на units.floor */
    "apartment_number": null,
    "finishing": null,
    "parking": null,
    "total_area": { "min": null, "max": null },  /* маппится на units.total_area */
    "living_area": { "min": null, "max": null },
    "kitchen_area": { "min": null, "max": null },
    "price_per_m2": { "min": null, "max": null },
    "price_full": { "min": null, "max": null },   /* маппится на units.price_full */
    "price_base": { "min": null, "max": null }
  }
}

Правила парсинга и маппинга (обязательно соблюдай при формировании JSON):
- Любые диапазоны (например "от 35 до 40 кв.м", "35–40 м²", "35-40") → unit_filters.total_area.min / .max (числа).
- Пределы по этажам ("не выше 5", "до 5 этажа") → unit_filters.floor.max = 5; ("этаж от 3") → unit_filters.floor.min = 3.
- Бюджет ("до 7 млн", "не больше 7000000") → unit_filters.price_full.max = 7000000 (число без разделителей). Поддерживай форматы с "млн", "₽", пробелами, запятыми.
- Если пользователь указывает конкретный ЖК/застройщика/тип дома/отделку — помещай это в соответствующие поля в complex (точное значение) **или** в complex_filters если речь про фильтр (например "только кирпично-монолитные" → complex_filters.building_type = "кирпично-монолитный").
- Если пользователь просит "ипотека" / "нужна ипотека" → complex_filters.payment_options = "Ипотека" (или просто "Ипотека").
- Регионы/города/районы → complex_filters.registration = "название региона/города" (строка).
- Если пользователь дал конкретные значения для отдельной квартиры (например "квартира номер 12 в корпусе 3") — заполняй поля в "unit" (не в фильтрах).
- Все числовые значения возвращай как числа (без единиц измерения). Если не уверена — ставь null.
- Никогда не возвращай текст вокруг JSON — только чистый JSON-объект.

Пример:
Ввод: "Подбери жк в Свердловской области, 35–40 кв.м, этаж не выше 5, нужна ипотека, бюджет до 7 млн"
Вывод:
{
  "complex_filters": {
    "url": null, "name": null, "address": null, "developer": null,
    "floor_count": { "min": null, "max": null }, "status": null, "key_issue": null,
    "parking": null, "ceiling_height": { "min": null, "max": null },
    "finishing": null, "contract_type": null, "building_type": null,
    "registration": "Свердловская область", "payment_options": "Ипотека",
    "units_total": { "min": null, "max": null }, "description": null,
    "contact_name": null, "contact_phone": null, "contact_email": null
  },
  "unit_filters": {
    "complex_id": null, "unit_type": null, "building": null, "section": null,
    "floor": { "min": null, "max": 5 },
    "apartment_number": null, "finishing": null, "parking": null,
    "total_area": { "min": 35, "max": 40 },
    "living_area": { "min": null, "max": null },
    "kitchen_area": { "min": null, "max": null },
    "price_per_m2": { "min": null, "max": null },
    "price_full": { "min": null, "max": null },
    "price_base": { "min": null, "max": null }
  }
}

Обрати внимание: в примере диапазоны и регион перенесены в соответствующие *_filters. Поля "complex" и "unit" оставлены для случаев, когда пользователь просит конкретные значения (напр., "покажи ЖК 'Сосновый бор'") — тогда в них нужно поставить точные строки/числа.

Теперь обработай запрос пользователя:
"%s"
""" % user_input

    response = await openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system",
                "content": "Ты — парсер пользовательских запросов по недвижимости."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content

    # Преобразуем из строки JSON в словарь
    import json
    try:
        parsed = json.loads(content)
    except Exception as e:
        print("Ошибка парсинга JSON:", e)
        return None

    return parsed


async def build_sql(filters: dict) -> tuple[str, dict]:
    where = []
    params = {}

    like_op = "LIKE"
    collate = " COLLATE NOCASE"

    # --------------------
    # complex_filters
    # --------------------
    cf = filters.get("complex_filters", {})
    mapping_complex = {
        "url": "c.url",
        "name": "c.name",
        "address": "c.address",
        "developer": "c.developer",
        "status": "c.status",
        "key_issue": "c.key_issue",
        "parking": "c.parking",
        "finishing": "c.finishing",
        "contract_type": "c.contract_type",
        "building_type": "c.building_type",
        "registration": "c.registration",
        "payment_options": "c.payment_options",
        "description": "c.description",
        "contact_name": "c.contact_name",
        "contact_phone": "c.contact_phone",
        "contact_email": "c.contact_email",
    }

    for key, column in mapping_complex.items():
        val = cf.get(key)
        if val:
            where.append(f"{column} {like_op} :{key}{collate}")
            params[key] = f"%{val}%"

    range_fields_complex = {
        "floor_count": "c.floor_count",
        "ceiling_height": "c.ceiling_height",
        "units_total": "c.units_total",
    }
    for key, column in range_fields_complex.items():
        rng = cf.get(key, {})
        if rng.get("min") is not None:
            where.append(f"{column} >= :{key}_min")
            params[f"{key}_min"] = rng["min"]
        if rng.get("max") is not None:
            where.append(f"{column} <= :{key}_max")
            params[f"{key}_max"] = rng["max"]

    # --------------------
    # unit_filters
    # --------------------
    uf = filters.get("unit_filters", {})
    mapping_unit = {
        "complex_id": "u.complex_id",
        "unit_type": "u.unit_type",
        "building": "u.building",
        "section": "u.section",
        "apartment_number": "u.apartment_number",
        "finishing": "u.finishing",
        "parking": "u.parking",
    }

    for key, column in mapping_unit.items():
        val = uf.get(key)
        if val:
            where.append(f"{column} {like_op} :{key}{collate}")
            params[key] = f"%{val}%"

    range_fields_unit = {
        "floor": "u.floor",
        "total_area": "u.total_area",
        "living_area": "u.living_area",
        "kitchen_area": "u.kitchen_area",
        "price_per_m2": "u.price_per_m2",
        "price_full": "u.price_full",
        "price_base": "u.price_base",
    }

    for key, column in range_fields_unit.items():
        rng = uf.get(key, {})
        if key == "floor":
            col_expr = "CAST(CASE WHEN instr(u.floor, '/') > 0 THEN substr(u.floor, 1, instr(u.floor, '/') - 1) ELSE u.floor END AS INTEGER)"
        elif key == "price_full":
            col_expr = "CAST(REPLACE(REPLACE(u.price_full, ' ', ''), char(160), '') AS INTEGER)"
        else:
            col_expr = column

        if rng.get("min") is not None:
            where.append(f"{col_expr} >= :{key}_min")
            params[f"{key}_min"] = rng["min"]
        if rng.get("max") is not None:
            where.append(f"{col_expr} <= :{key}_max")
            params[f"{key}_max"] = rng["max"]

    sql = """
    SELECT 
        c.url, c.name, c.address, c.registration, c.building_type, c.payment_options,
        c.contact_name, c.contact_phone, c.contact_email,
        u.unit_type, u.total_area, u.floor, u.price_full, u.building,
        u.apartment_number
    FROM complexes c
    JOIN units u ON u.complex_id = c.id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)

    return sql, params


# =====================
# Форматирование страниц
# =====================
def format_apartments(apartments: list, start: int = 0, limit: int = 10):
    page_items = apartments[start:start+limit]
    text_lines = [f'Найдено квартир: {len(apartments)}\n']

    for i, apt in enumerate(page_items, start=start+1):
        if apt["contact_name"] and apt["contact_phone"] and apt["contact_email"]:
            contact_info = (
                f'Менеджер {apt["contact_name"]}\n'
                f'{apt["contact_phone"]} | {apt["contact_email"]}\n'
            )
        line = (
            f'<a href="{apt["url"]}">{apt["name"]}</a>\n'
            f'Адрес: {apt["address"]}, {apt["building"]}, кв {apt["apartment_number"]}\n'
            f'Цена: {apt["price_full"]}, {apt["unit_type"]}\n'
            f'Площадь: {apt["total_area"]} м², Этаж: {apt["floor"]}\n'
            f'Тип дома: {apt["building_type"]}\n'
            f'Способ оплаты: {apt["payment_options"]}\n'
            f'{contact_info}'
        )
        text_lines.append(line)
    text = "\n".join(text_lines)

    # Кнопки навигации в одну строку
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = []

    if start > 0:
        buttons.append(InlineKeyboardButton(
            text="⬅ Предыдущие 10",
            callback_data=f"page:{max(0, start-10)}"
        ))

    if start + limit < len(apartments):
        buttons.append(InlineKeyboardButton(
            text="Следующие 10 ➡",
            callback_data=f"page:{start+limit}"
        ))

    if buttons:
        keyboard.row(*buttons)  # добавляем все кнопки одной строкой
    keyboard.row(mainmenu_btn)

    return text, keyboard


def _get_vectordb():
    embeddings = OpenAIEmbeddings()
    return FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)


def _semantic_search(query: str, top_k: int = 8, segment: str | None = None):
    vectordb = _get_vectordb()
    flt = {"segment": segment} if segment else None
    return vectordb.similarity_search(query, k=top_k, filter=flt)


async def request_floor_func(message, state):
    try:
        docs = _semantic_search(message.text, top_k=8, segment="real_estate")
    except Exception as e:
        print(e)
        await message.reply("❌ Индекс недоступен. Повторите позже.")
        return

    if not docs:
        await message.reply("❌ Ничего подходящего не найдено в базе знаний.")
        return

    context = "\n\n".join([d.page_content[:1000] for d in docs])
    prompt = (
        f"Запрос по недвижимости: {message.text}\n\n"
        f"Контекст из базы знаний:\n{context}\n\n"
        f"Сформируй понятный ответ (5–8 предложений) на русском с ориентировками по цене/условиям, краткой сводкой по ЖК и предложи следующий шаг."
    )

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты — помощник по недвижимости."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )
    answer = response.choices[0].message.content
    await message.reply(answer or "Нет подходящих вариантов", parse_mode="HTML")


# =====================
# Обработчик пагинации
# =====================
async def paginate_apartments(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    apartments = data.get("apartments", [])
    if not apartments:
        await callback.message.edit_text("❌ Данные недоступны")
        await callback.answer()
        return

    # Извлекаем start из callback_data "page:0", "page:10" ...
    start = int(callback.data.split(":")[1])

    text, keyboard = format_apartments(apartments, start=start)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()


async def request_info_func(message, state):

    # 1. Загружаем лекции
    conn = sqlite3.connect(DB_PATH_AUDIO)
    cur = conn.cursor()
    cur.execute("SELECT file_name, audio_text FROM audio_files")
    lectures = cur.fetchall()
    conn.close()

    if not lectures:
        await message.reply("❌ В базе нет лекций.")
        return

    # 2. Формируем prompt для GPT
    lectures_text = "\n\n".join(
        [f"Лекция: {str(file_name).split('.')[0]}\nТекст: {audio_text[:1000]}..." for file_name,
         audio_text in lectures]
    )

    prompt = f"""
Ты — интеллектуальный помощник. Пользователь задаёт вопрос, а у тебя есть база лекций (их транскрипт).

Задача:
1. Найди в этих лекциях, есть ли ответ на вопрос пользователя.
2. Если ответ есть — укажи, в какой лекции это было.
3. Приведи краткую выдержку (2–3 предложения) из текста, где упоминается ответ.
4. Отвечай строго по формату:

Ответ: <текст ответа или "ничего не найдено">
Лекция: <название лекции или "нет">
Фрагмент: <короткая выдержка или пусто>

Вопрос пользователя:
"{message.text}"

Лекции:
{lectures_text}
"""

    # 3. Отправляем в OpenAI
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",  # быстрый и дешёвый, можешь заменить на gpt-4
        messages=[
            {"role": "system", "content": "Ты — интеллектуальный поиск по лекциям."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    answer = response.choices[0].message.content

    await message.reply(answer, parse_mode="HTML")


def register_request_from_db(dp: Dispatcher):
    dp.register_callback_query_handler(
        paginate_apartments, lambda c: c.data.startswith("page:"), state='*')
