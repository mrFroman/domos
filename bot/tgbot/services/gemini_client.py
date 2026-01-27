import re
from typing import Optional
from openai import OpenAI
import os
import uuid
import base64
from PIL import Image

from bot.tgbot.services.watermark import WatermarkService
from config import BASE_DIR, load_config, logger_bot


config = load_config(os.path.join(BASE_DIR, ".env"))

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=config.open_ai.token,
)
logo_path = os.path.join(
    BASE_DIR,
    "bot",
    "tgbot",
    "DomosClubLogo.jpg",
)

compas_path = os.path.join(
    BASE_DIR,
    "bot",
    "tgbot",
    "compas.png",
)

style_image_path = os.path.join(
    BASE_DIR,
    "floor.png",
)


def force_black_walls_white_background(image_path: str) -> None:
    """
    Приводит сгенерированное изображение плана к чёрно‑белому стилю:
    чёрные линии, белый фон.
    """
    try:
        img = Image.open(image_path).convert("L")  # градации серого

        # Простой порог: фон светлый → становится чисто белым, линии тёмные → чёрные
        threshold = 200
        bw = img.point(lambda v: 255 if v > threshold else 0, mode="L")

        bw.save(image_path, format="JPEG", quality=95)
    except Exception as e:
        logger_bot.info(f"[Plan B/W normalize error] {e}")

DIRECTION_ANGLES = {
    "север": 0,
    "северо-восток": -45,
    "восток": -90,
    "юго-восток": -135,
    "юг": 180,
    "юго-запад": 135,
    "запад": 90,
    "северо-запад": 45,
}

def parse_north_angle(text: str) -> Optional[int]:
    """
    Возвращает угол поворота компаса (в градусах),
    исходя из того, где находится СЕВЕР на плане.
    """

    if not text:
        return None

    t = text.lower()
    t = t.replace("ё", "е")
    t = t.replace("-", " ")      # дефис → пробел
    t = re.sub(r"[,:;]", " ", t)  # убираем знаки препинания
    t = re.sub(r"\s+", " ", t).strip()  # многократные пробелы → один

    # 1. Явные указания положения
    explicit = {
        "север сверху": 0,
        "север снизу": 180,
        "север справа": -90,
        "север слева": 90,
    }
    for key, angle in explicit.items():
        if key in t:
            return angle

    # 2. Сложные направления (на юго-западе и т.п.)
    directions_sorted = sorted(DIRECTION_ANGLES.keys(), key=len, reverse=True)
    for direction in directions_sorted:
        # нормализуем ключ
        direction_norm = direction.replace("-", " ")
        if direction_norm in t:
            return DIRECTION_ANGLES[direction]

        # поддержка "на юго западе", "в юго востоке"
        if f"на {direction_norm}" in t or f"в {direction_norm}" in t:
            return DIRECTION_ANGLES[direction]

    return None


def remove_directions(text: str) -> str:
    """
    Убирает упоминания сторон света из текста пользователя,
    чтобы они не попадали в промпт для модели.
    """
    if not text:
        return ""

    t = text.lower()
    t = t.replace("ё", "е")

    # паттерн для удаления фраз типа:
    # "стороны света: север снизу", "на юго-западе", "север справа"
    pattern = r"(стороны света\s*[:\-]?\s*\w+(\s+\w+)*|на\s+\w+(\s+\w+)*|в\s+\w+(\s+\w+)*)"
    clean_text = re.sub(pattern, "", t, flags=re.IGNORECASE)

    # удаляем лишние пробелы
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    return clean_text


# MODEL_NAME = "google/gemini-2.5-flash-image-preview"
MODEL_NAME = "google/gemini-2.5-flash-image"
# MODEL_NAME = "openai/gpt-5-image"
# MODEL_NAME = "openai/gpt-5-image-mini"

PROMPT_OLD = """Преобразуй этот эскиз планировки в профессиональный архитектурно-технический чертёж. Первое изображение это эскиз, а второе изображение это пример стиля.

СТИЛЬ:
- Чёткие и прямые чёрные линии на белом фоне, в стиле загруженного примера.
- Чистый технический план с плоским ортогональным видом сверху, пригодный для печати и импорта в CAD.
- На чертеже не должно лить текста, цифр и внешних элементов.

ФОРМАТ:
- Высококачественный JPEG (.jpg), белый фон, без прозрачности. Планировка должна быть по центру и не обрезана.

Выполни всё в соответствии с указаниями пользователя:
"""


PROMPT2 = """Задача: аккуратно ПЕРЕРИСОВАТЬ исходный чертёж с изображения.

ИСТОЧНИК:
- Первое изображение — единственный источник информации.
- Второе изображение (если есть) — только пример толщины и стиля линий.

ОСНОВНОЕ ПРАВИЛО:
- Делай ТОЛЬКО то, что есть на исходном изображении.
- Ничего не добавляй.
- Ничего не убирай.

ГЕОМЕТРИЯ:
- Восстанови внешние стены как прямые линии, основываясь на их общем направлении.
- Исправь искажения фото (перспектива, изгиб листа, складки бумаги).
- При выпрямлении НЕ меняй относительные размеры и пропорции.
- Все углы стен должны быть строго 90°, если на эскизе нет явного наклона.

ОБЯЗАТЕЛЬНО СОХРАНИТЬ:
- Все внешние и внутренние стены.
- Все двери, включая направление открывания.
- Все проёмы.
- Все размерные линии и все числовые значения размеров.
- Все подписи, если они есть на эскизе.

ЗАПРЕЩЕНО:
- Удалять двери или размеры.
- Добавлять мебель, оси, сетки, масштаб, рамки.
- Додумывать недостающие элементы.
- Оптимизировать или упрощать план.

СТИЛЬ:
- Чёрные линии на белом фоне.
- Ортогональный вид сверху.
- Одинаковая толщина линий.
- Без цвета, теней, текстур и эффектов.

РЕЗУЛЬТАТ:
- Плоский технический чертёж.
- Высокая чёткость линий.
- Белый фон.
- Весь чертёж целиком в кадре, без обрезки.
- Текст должен быть в едином стиле CAD

КРИТИЧЕСКОЕ:
Это не редизайн и не интерпретация. Это чистая перерисовка.
Любое удаление элементов считается ошибкой.

ПРИОРИТЕТ:
- Внешний контур здания имеет наивысший приоритет.
- Сначала восстанови внешний контур как замкнутый прямоугольный/ортогональный контур.
- Только после этого перерисовывай внутренние стены и элементы.
"""


PROMPT3 = """
TASK:
Redraw the input image exactly as a clean technical drawing.

INPUT:
- First image is the only source of geometry and data.

RULES:
- Copy all visible lines and symbols from the input.
- Do not invent, add, remove, simplify or optimize anything.
- If an element exists in the image, it must exist in the output.
- If an element does not exist in the image, it must not appear in the output.

GEOMETRY NORMALIZATION:
- Remove photo distortions (perspective, paper bends, camera angle).
- Convert all walls to straight orthogonal lines.
- All wall angles must be 90 degrees unless a clear non-orthogonal angle is visible in the input.
- Preserve relative proportions and positions.

PRIORITY:
1. Outer walls (closed contour).
2. Inner walls.
3. Doors and openings (including swing direction).
4. Dimension lines and numeric values.
5. Text annotations.

DOORS:
- Keep all doors.
- Keep door positions and opening directions.
- Do not remove or change doors.

DIMENSIONS:
- Keep all dimension lines.
- Keep all arrows and extension lines.
- Keep all numeric dimension values exactly as written.

STYLE:
- Black lines only.
- White background only.
- No color.
- No shading.
- No textures.
- No perspective.
- Top-down orthographic view.
- Uniform line thickness.
- Text only CAD style.

OUTPUT:
- Flat 2D drawing.
- Entire drawing fully visible.
- No cropping.
- Centered on canvas.
- High line clarity.

CRITICAL:
This is not interpretation.
This is not redesign.
This is strict redrawing.
Any missing or extra element is an error.

"""


PROMPT = """
Три обязательных правила. Нарушать нельзя.

ПРАВИЛО 1 — ЕДИНЫЙ Ч/Б СТИЛЬ:
- У тебя два изображения: (1) план квартиры пользователя, (2) образец стиля.
- Стиль линий и текста на результате всегда один и тот же: белый фон, только чёрные
  линии. Никаких серых, цветных линий, текстур, заливок и теней.
- Все стены, контуры мебели, размерные линии и весь текст рисуются только чёрным по
  абсолютно белому фону. Остальные области должны быть чисто белыми.
- Из образца стиля берёшь только внешний вид линий и подписей (толщина линий, вид
  шрифта). Планировку и мебель из образца не копируешь.

ПРАВИЛО 2 — НЕ ДВИГАТЬ:
- Предметы и мебель должны оставаться на тех же местах, в той же ориентации.
- Запрещено двигать, перемещать, поворачивать, переворачивать стены, двери, окна,
  мебель (кровати, диваны, столы, шкафы и т.п.). Рисуешь каждый объект там же, где
  он на присланном плане.

ПРАВИЛО 3 — НЕ ДОБАВЛЯТЬ ТЕКСТ:
- Надписи и размеры рисуешь только если они есть на присланной пользователем картинке.
- Запрещено придумывать новую текстовую информацию: нельзя добавлять подписи комнат,
  новые слова, переводы (например, «living room»), сокращения, дополнительные числа
  или пояснения, если их нет на исходном изображении.
- Нельзя менять текстовое содержимое: не переводить, не перефразировать, не заменять
  слова и числа на другие значения.

ЧТО ДЕЛАТЬ:
- Перерисовать присланный план в стиле образца: те же линии и тот же вид текста.
- Сохранить всё на тех же местах. Удалить все цвета/текстуры и оставить только
  чёрные линии на белом фоне. Не добавлять лишнего.
- Любой текст на плане (рукописный или печатный) переписать аккуратным печатным
  шрифтом (как на образце стиля), посимвольно сохраняя те же слова и те же числовые
  значения. Можно очищать написание, но нельзя менять смысл и добавлять новые слова.
"""

async def generate_plan_from_image(image_path: str, text: str) -> str:
    user_prompt = remove_directions(text)
    base_prompt = PROMPT + user_prompt
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")

        # style reference image (for unified line/text style only)
        try:
            with open(style_image_path, "rb") as sf:
                style_bytes = sf.read()
            encoded_style_image = base64.b64encode(style_bytes).decode("utf-8")
        except Exception:
            encoded_style_image = None

        max_attempts = 5

        current_prompt = base_prompt

        for attempt in range(1, max_attempts + 1):
            logger_bot.info(
                "🎨 ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЯ, попытка " f"{attempt}/{max_attempts}"
            )
            response = client.chat.completions.create(
                model=MODEL_NAME,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            [
                                {
                                    "type": "text",
                                    "text": current_prompt,
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": (
                                            "data:image/jpeg;base64," f"{encoded_image}"
                                        ),
                                        "detail": "high",
                                    },
                                },
                            ]
                            + (
                                [
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": (
                                                "data:image/png;base64,"
                                                f"{encoded_style_image}"
                                            ),
                                            "detail": "high",
                                        },
                                    }
                                ]
                                if encoded_style_image
                                else []
                            )
                        ),
                    },
                ],
            )

            choice = response.choices[0].message
            logger_bot.info("[INFO] проверка блоков ответа на наличие изображения")
            content_blocks = getattr(choice, "content", None)

            if isinstance(content_blocks, list):
                for block in content_blocks:
                    block_type = block.get("type")
                    if block_type in {
                        "output_image_url",
                        "image_url",
                    }:
                        url_or_data = block.get("image_url", {}).get("url")
                        if url_or_data and url_or_data.startswith("data:image"):
                            prefix, b64data = url_or_data.split(",", 1)
                            img_bytes = base64.b64decode(b64data)

                            # Если модель вернула байты, совпадающие с исходным изображением,
                            # считаем это ошибкой (она просто отдала вход) и пробуем ещё раз
                            if img_bytes == image_bytes:
                                logger_bot.info(
                                    "[WARN] Модель вернула исходное изображение без изменений, усиливаем инструкцию и повторяем попытку."
                                )
                                current_prompt = (
                                    base_prompt
                                    + "\n\nCRITICAL: You incorrectly returned the original image. "
                                    "You MUST redraw it in the unified CAD style with normalized line and text style. "
                                    "Do NOT return the input image or a pixel-identical copy."
                                )
                                break

                            out_path = f"outputs/plan_{uuid.uuid4().hex}.jpg"
                            os.makedirs("outputs", exist_ok=True)
                            with open(out_path, "wb") as wf:
                                wf.write(img_bytes)

                            # Жёстко приводим план к чёрным линиям на белом фоне
                            force_black_walls_white_background(out_path)

                            await WatermarkService.add_corner_logo(
                                image_path=str(out_path),
                                output_path=out_path,
                                logo_path=str(logo_path),
                                position="bottom-right",
                                margin=20,
                                logo_scale=0.10,
                            )

                            angle = parse_north_angle(text)
                            
                            await WatermarkService.add_compass_image(
                                image_path=str(out_path),
                                output_path=out_path,
                                compass_path=compas_path,
                                north_angle=angle or 0,           # север слева
                                position="top-left",    # противоположный угол
                                scale=0.12,
                                opacity=0.85,
                                margin=20,
                            )

                            return out_path

            # fallback to legacy OpenAI SDK images field if present
            if hasattr(choice, "images") and choice.images:
                image_info = choice.images[0]
                url_or_data = image_info.get("image_url", {}).get("url")
                if url_or_data and url_or_data.startswith("data:image"):
                    prefix, b64data = url_or_data.split(",", 1)
                    img_bytes = base64.b64decode(b64data)
                    out_path = f"outputs/plan_{uuid.uuid4().hex}.jpg"
                    os.makedirs("outputs", exist_ok=True)
                    with open(out_path, "wb") as wf:
                        wf.write(img_bytes)

                    # Жёстко приводим план к чёрным линиям на белом фоне
                    force_black_walls_white_background(out_path)

                    await WatermarkService.add_corner_logo(
                        image_path=str(out_path),
                        output_path=out_path,
                        logo_path=str(logo_path),
                        position="bottom-right",
                        margin=20,
                        logo_scale=0.10,
                    )

                    angle = parse_north_angle(text)
                    
                    await WatermarkService.add_compass_image(
                        image_path=str(out_path),
                        output_path=out_path,
                        compass_path=compas_path,
                        north_angle=angle or 0,           # север слева
                        position="top-left",    # противоположный угол
                        scale=0.12,
                        opacity=0.85,
                        margin=20,
                    )

                    return out_path

            logger_bot.info("[WARN] Попытка без изображения, повторяем запрос.")

        logger_bot.info("[WARN] Превышен лимит попыток генерации изображения.")
        return None

    except Exception as e:
        logger_bot.info(f"[OpenRouter Gemini Error] {e}")
        return None
