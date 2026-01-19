import cv2
import numpy as np
import uuid
import os


async def process_image(path: str) -> str:
    """
    Упрощённая обработка: выделение контуров и генерация "технического" JPEG-чертежа
    """
    try:
        # Загрузка изображения
        image = cv2.imread(path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Увеличение контраста
        gray = cv2.equalizeHist(gray)

        # Бинаризация
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        # Найдём контуры
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Пустой холст (белый фон)
        height, width = gray.shape
        plan = np.ones((height, width, 3), dtype=np.uint8) * 255

        # Нарисуем контуры как линии
        cv2.drawContours(plan, contours, -1, (0, 0, 0), thickness=2)

        # Сохраняем
        output_path = f"outputs/plan_{uuid.uuid4().hex}.jpg"
        os.makedirs("outputs", exist_ok=True)
        cv2.imwrite(output_path, plan)

        return output_path
    except Exception as e:
        print(f"[ERROR] process_image: {e}")
        return None
