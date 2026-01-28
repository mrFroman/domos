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
    Постобработка: улучшает качество, резкость и контраст.
    Сохраняет в PNG для максимального качества.
    """
    try:
        from PIL import ImageFilter, ImageOps, ImageEnhance
        
        # Открываем изображение
        img = Image.open(image_path)
        
        # 1. Увеличиваем контраст для чёткости
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        
        # 2. Увеличиваем резкость
        sharpness = ImageEnhance.Sharpness(img)
        img = sharpness.enhance(1.5)
        
        # 3. Делаем фон чище (автоуровни)
        img = ImageOps.autocontrast(img, cutoff=0.5)
        
        # 4. Сохраняем как PNG (без потери качества)
        png_path = image_path.rsplit('.', 1)[0] + '.png'
        img.save(png_path, format="PNG", optimize=True)
        
        # Удаляем старый jpg если он отличается
        import os
        if png_path != image_path and os.path.exists(image_path):
            os.remove(image_path)
        
        logger_bot.info("[Plan] Качество улучшено, сохранено как PNG")
        return png_path
    except Exception as e:
        logger_bot.info(f"[Plan normalize error] {e}")
        return image_path

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
ENHANCE this floor plan image.

IMPROVE (make better looking):
✓ Lines - make them straight, clean, sharp
✓ Furniture shapes - make them cleaner, more detailed
✓ Walls - make them uniform dark gray
✓ Background - make it pure white
✓ Overall quality - high resolution, professional look

TEXT RULES - VERY IMPORTANT:
✓ ONLY redraw text that is CLEARLY VISIBLE on the original image
✓ ALL text must use EXACTLY this font: Arial Bold, BLACK color, size 12-14pt
✓ UNIFIED FONT - every single text element uses the same Arial Bold
✓ Numbers, labels, dimensions - all Arial Bold
✓ Keep text in SAME position
✓ Keep SAME text content (same words, same numbers)
✗ If text is unclear or unreadable - LEAVE IT BLANK, do not write anything
✗ NEVER add your own text
✗ NEVER write room names (like "kitchen", "bedroom", "bathroom")
✗ NEVER add labels or annotations
✗ NEVER guess what text should say

DO NOT CHANGE:
✗ Positions - everything stays in same place
✗ Layout - same room arrangement
✗ Object count - same number of items
✗ Nothing moves left/right/up/down

ABSOLUTELY FORBIDDEN - ZERO TOLERANCE:
✗ WRITING ANY NEW TEXT that was not on the original
✗ Adding room names or labels
✗ Adding dimensions that were not there
✗ Moving furniture to different location
✗ Adding new furniture
✗ Removing any objects
✗ Rotating objects

SIMPLE RULE:
Same picture, better quality.
If no text on original - no text on result.
Enhance, don't redesign.
"""

async def generate_plan_from_image(image_path: str, text: str) -> str:
    user_prompt = remove_directions(text)
    base_prompt = PROMPT + user_prompt
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")

        # НЕ отправляем style reference - описываем стиль текстом
        style_bytes = None
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
                                    "[WARN] Модель вернула исходное изображение без изменений, повторяем попытку."
                                )
                                current_prompt = (
                                    base_prompt
                                    + "\n\nCRITICAL: You returned the original input image. "
                                    "You MUST redraw it in the style of Image 2. "
                                    "Do NOT return the input image."
                                )
                                break
                            
                            # Если модель вернула образец стиля (floor.png) - это тоже ошибка
                            if style_bytes and img_bytes == style_bytes:
                                logger_bot.info(
                                    "[WARN] Модель вернула образец стиля (floor.png), повторяем попытку."
                                )
                                current_prompt = (
                                    base_prompt
                                    + "\n\nCRITICAL: You returned the style reference image (Image 2). "
                                    "You MUST redraw Image 1 using the style of Image 2. "
                                    "Do NOT return Image 2 itself."
                                )
                                break

                            out_path = f"outputs/plan_{uuid.uuid4().hex}.png"
                            os.makedirs("outputs", exist_ok=True)
                            with open(out_path, "wb") as wf:
                                wf.write(img_bytes)

                            # Улучшаем качество и сохраняем как PNG
                            out_path = force_black_walls_white_background(out_path) or out_path

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
                    
                    # Проверка: не вернула ли модель исходное изображение или образец стиля
                    if img_bytes == image_bytes:
                        logger_bot.info("[WARN] Fallback: модель вернула исходное изображение")
                        continue
                    if style_bytes and img_bytes == style_bytes:
                        logger_bot.info("[WARN] Fallback: модель вернула образец стиля")
                        continue
                    
                    out_path = f"outputs/plan_{uuid.uuid4().hex}.png"
                    os.makedirs("outputs", exist_ok=True)
                    with open(out_path, "wb") as wf:
                        wf.write(img_bytes)

                    # Улучшаем качество и сохраняем как PNG
                    out_path = force_black_walls_white_background(out_path) or out_path

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
