from openai import OpenAI
import os
import uuid
import base64

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

MODEL_NAME = "google/gemini-2.5-flash-image-preview"
# MODEL_NAME = "openai/gpt-5-image"
# MODEL_NAME = "openai/gpt-5-image-mini"

PROMPT = """Преобразуй этот эскиз планировки в профессиональный архитектурно-технический чертёж. Первое изображение это эскиз, а второе изображение это пример стиля.

СТИЛЬ:
- Чёткие и прямые чёрные линии на белом фоне, в стиле загруженного примера.
- Чистый технический план с плоским ортогональным видом сверху, пригодный для печати и импорта в CAD.
- На чертеже не должно лить текста, цифр и внешних элементов.

ФОРМАТ:
- Высококачественный JPEG (.jpg), белый фон, без прозрачности. Планировка должна быть по центру и не обрезана.

Выполни всё в соответствии с указаниями пользователя:
"""


async def generate_plan_from_image(image_path: str, text: str) -> str:
    user_prompt = text
    final_prompt = PROMPT + user_prompt
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        with open(
            os.path.join(
                BASE_DIR,
                "floor.png",
            ),
            "rb",
        ) as f:
            example_bytes = f.read()
        encoded_example = base64.b64encode(example_bytes).decode("utf-8")

        max_attempts = 5

        for attempt in range(1, max_attempts + 1):
            logger_bot.info(
                "🎨 ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЯ, попытка " f"{attempt}/{max_attempts}"
            )
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": final_prompt,
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
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_example}",
                                    "detail": "high",
                                },
                            },
                        ],
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
                            out_path = f"outputs/plan_{uuid.uuid4().hex}.jpg"
                            os.makedirs("outputs", exist_ok=True)
                            with open(out_path, "wb") as wf:
                                wf.write(img_bytes)
                            await WatermarkService.add_corner_logo(
                                image_path=str(out_path),
                                output_path=out_path,
                                logo_path=str(logo_path),
                                position="bottom-right",
                                margin=20,
                                logo_scale=0.10,
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
                    await WatermarkService.add_corner_logo(
                        image_path=str(out_path),
                        output_path=out_path,
                        logo_path=str(logo_path),
                        position="bottom-right",
                        margin=20,
                        logo_scale=0.10,
                    )
                    return out_path

            logger_bot.info("[WARN] Попытка без изображения, повторяем запрос.")

        logger_bot.info("[WARN] Превышен лимит попыток генерации изображения.")
        return None

    except Exception as e:
        logger_bot.info(f"[OpenRouter Gemini Error] {e}")
        return None
