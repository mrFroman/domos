"""
Watermark Service - добавление водяных знаков на изображения
"""

from pathlib import Path
from typing import Optional

import aiofiles
from PIL import Image, ImageDraw, ImageFont
import io


class WatermarkService:
    """
    Сервис для добавления водяных знаков на изображения
    """

    @staticmethod
    async def add_watermark(
        image_path: str,
        output_path: str,
        watermark_text: Optional[str] = None,
        opacity: Optional[float] = None,
        font_size: Optional[int] = None,
    ) -> bool:
        """
        Добавить водяной знак на изображение

        Args:
            image_path: Путь к исходному изображению
            output_path: Путь для сохранения результата
            watermark_text: Текст водяного знака (по умолчанию из настроек)
            opacity: Прозрачность водяного знака 0-1 (по умолчанию из настроек)
            font_size: Размер шрифта (по умолчанию из настроек)

        Returns:
            True если успешно
        """
        try:
            # Параметры по умолчанию из настроек
            if watermark_text is None:
                watermark_text = "DomosClub"
            if opacity is None:
                opacity = 0.4
            if font_size is None:
                font_size = 48

            # Читаем изображение
            async with aiofiles.open(image_path, "rb") as f:
                image_data = await f.read()

            # Открываем изображение
            image = Image.open(io.BytesIO(image_data))

            # Конвертируем в RGBA для прозрачности
            if image.mode != "RGBA":
                image = image.convert("RGBA")

            # Создаём слой для водяного знака
            watermark_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark_layer)

            # Пробуем загрузить шрифт
            try:
                # Используем стандартный шрифт Arial/DejaVu
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", font_size)
                except Exception:
                    # Используем стандартный шрифт
                    font = ImageFont.load_default()

            # Вычисляем размер текста
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Позиция водяного знака (правый нижний угол с отступом)
            margin = 20
            x = image.width - text_width - margin
            y = image.height - text_height - margin

            # Рисуем полупрозрачный текст
            alpha = int(255 * opacity)
            text_color = (255, 255, 255, alpha)  # Белый цвет с прозрачностью

            # Добавляем тень для лучшей читаемости
            shadow_offset = 2
            shadow_color = (0, 0, 0, int(alpha * 0.5))
            draw.text(
                (x + shadow_offset, y + shadow_offset),
                watermark_text,
                font=font,
                fill=shadow_color,
            )

            # Основной текст
            draw.text((x, y), watermark_text, font=font, fill=text_color)

            # Объединяем слои
            watermarked = Image.alpha_composite(image, watermark_layer)

            # Конвертируем обратно в RGB для сохранения в JPEG
            if watermarked.mode == "RGBA":
                watermarked = watermarked.convert("RGB")

            # Сохраняем результат
            output_buffer = io.BytesIO()
            watermarked.save(output_buffer, format="JPEG", quality=95)

            # Записываем в файл
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(output_path, "wb") as f:
                await f.write(output_buffer.getvalue())

            return True

        except Exception as e:
            print(f"Error adding watermark: {e}")
            return False

    @staticmethod
    async def add_corner_logo(
        image_path: str,
        output_path: str,
        logo_path: str,
        position: str = "bottom-right",
        margin: int = 20,
        logo_scale: float = 0.15,
    ) -> bool:
        """
        Добавить логотип в угол изображения

        Args:
            image_path: Путь к исходному изображению
            output_path: Путь для сохранения результата
            logo_path: Путь к логотипу
            position: Позиция логотипа (bottom-right, bottom-left, top-right, top-left)
            margin: Отступ от краёв
            logo_scale: Масштаб логотипа относительно изображения

        Returns:
            True если успешно
        """
        try:
            # Читаем изображение и логотип
            async with aiofiles.open(image_path, "rb") as f:
                image_data = await f.read()

            async with aiofiles.open(logo_path, "rb") as f:
                logo_data = await f.read()

            # Открываем изображения
            image = Image.open(io.BytesIO(image_data))
            logo = Image.open(io.BytesIO(logo_data))

            # Конвертируем в RGBA
            if image.mode != "RGBA":
                image = image.convert("RGBA")
            if logo.mode != "RGBA":
                logo = logo.convert("RGBA")

            # Масштабируем логотип
            logo_width = int(image.width * logo_scale)
            aspect_ratio = logo.height / logo.width
            logo_height = int(logo_width * aspect_ratio)
            logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

            # Вычисляем позицию
            if position == "bottom-right":
                x = image.width - logo_width - margin
                y = image.height - logo_height - margin
            elif position == "bottom-left":
                x = margin
                y = image.height - logo_height - margin
            elif position == "top-right":
                x = image.width - logo_width - margin
                y = margin
            else:  # top-left
                x = margin
                y = margin

            # Накладываем логотип
            image.paste(logo, (x, y), logo)

            # Конвертируем обратно в RGB
            if image.mode == "RGBA":
                image = image.convert("RGB")

            # Сохраняем результат
            output_buffer = io.BytesIO()
            image.save(output_buffer, format="JPEG", quality=95)

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(output_path, "wb") as f:
                await f.write(output_buffer.getvalue())

            return True

        except Exception as e:
            print(f"Error adding logo: {e}")
            return False
    
    @staticmethod
    async def add_compass_image(
        image_path: str,
        output_path: str,
        compass_path: str,
        north_angle: Optional[float] = 0,   # угол в градусах
        position: str = "top-left",
        scale: float = 0.15,
        opacity: float = 0.9,
        margin: int = 20,
    ) -> bool:
        """
        Добавляет круглый компас на изображение с возможностью поворота под любой угол.
        
        Args:
            image_path: путь к исходному изображению
            output_path: путь для сохранения результата
            compass_path: путь к изображению компаса (круглый PNG)
            north_angle: угол поворота компаса (0° = север вверх)
            position: позиция компаса на изображении (top-left, top-right, bottom-left, bottom-right)
            scale: масштаб компаса относительно ширины изображения
            opacity: прозрачность компаса (0-1)
            margin: отступ от краёв изображения
        """
        try:
            # Чтение исходного изображения и компаса
            async with aiofiles.open(image_path, "rb") as f:
                image_data = await f.read()
            async with aiofiles.open(compass_path, "rb") as f:
                compass_data = await f.read()

            image = Image.open(io.BytesIO(image_data)).convert("RGBA")
            compass = Image.open(io.BytesIO(compass_data)).convert("RGBA")

            # Масштаб компаса
            target_width = int(image.width * scale)
            ratio = compass.height / compass.width
            target_height = int(target_width * ratio)
            compass = compass.resize((target_width, target_height), Image.Resampling.LANCZOS)

            # Поворот под север
            if north_angle:
                compass = compass.rotate(north_angle, expand=True, resample=Image.Resampling.BICUBIC)

            # Прозрачность
            if opacity < 1:
                alpha = compass.getchannel("A")
                alpha = alpha.point(lambda p: int(p * opacity))
                compass.putalpha(alpha)

            # Вычисляем позицию
            if position == "top-left":
                x, y = margin, margin
            elif position == "top-right":
                x, y = image.width - compass.width - margin, margin
            elif position == "bottom-left":
                x, y = margin, image.height - compass.height - margin
            else:  # bottom-right
                x, y = image.width - compass.width - margin, image.height - compass.height - margin

            # Накладываем компас
            image.alpha_composite(compass, (x, y))

            # Сохраняем как JPEG
            result_image = image.convert("RGB")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(output_path, "wb") as f:
                buffer = io.BytesIO()
                result_image.save(buffer, format="JPEG", quality=95)
                await f.write(buffer.getvalue())

            return True

        except Exception as e:
            print(f"Error adding compass image: {e}")
            return False