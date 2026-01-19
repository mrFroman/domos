import base64
import uuid
import os


async def save_base64_image_from_response(response):
    try:
        message = response.choices[0].message

        print(f'{message=}')

        if not message.reasoning_details:
            print("❌ Нет reasoning_details — не найдено изображение.")
            return None

        data = message.reasoning_details[0]["data"]

        if not data or "image" not in data:
            print("❌ Нет поля 'image' в reasoning_details.")
            return None

        # Извлекаем base64 изображения
        b64_img = data["image"]

        # Сохраняем файл
        output_path = f"outputs/plan_{uuid.uuid4().hex}.jpg"
        os.makedirs("outputs", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(b64_img))

        return output_path

    except Exception as e:
        print(f"[Parser error] {e}")
        return None
