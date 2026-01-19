#!/usr/bin/env python3
"""
Скрипт для создания иконок PWA из исходного логотипа
"""
import os
from PIL import Image

def create_icons():
    """Создает иконки разных размеров для PWA"""
    input_path = "2026-01-16 11.10.28.jpg"
    output_dir = "static/icons"
    
    # Создаем директорию если её нет
    os.makedirs(output_dir, exist_ok=True)
    
    # Размеры иконок для разных устройств
    sizes = [
        (192, 192, "icon-192.png"),
        (512, 512, "icon-512.png"),
        (180, 180, "apple-touch-icon.png"),  # iOS
        (152, 152, "icon-152.png"),
        (144, 144, "icon-144.png"),
        (120, 120, "icon-120.png"),
        (114, 114, "icon-114.png"),
        (76, 76, "icon-76.png"),
        (72, 72, "icon-72.png"),
        (60, 60, "icon-60.png"),
        (57, 57, "icon-57.png"),
    ]
    
    if not os.path.exists(input_path):
        print(f"Ошибка: файл {input_path} не найден!")
        return
    
    try:
        # Открываем исходное изображение
        img = Image.open(input_path)
        
        # Конвертируем в RGB если нужно
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Создаем иконки всех размеров
        for width, height, filename in sizes:
            # Изменяем размер с сохранением пропорций
            resized = img.resize((width, height), Image.Resampling.LANCZOS)
            
            # Сохраняем как PNG
            output_path = os.path.join(output_dir, filename)
            resized.save(output_path, "PNG", optimize=True)
            print(f"Создана иконка: {output_path} ({width}x{height})")
        
        print("\nВсе иконки успешно созданы!")
        
    except Exception as e:
        print(f"Ошибка при создании иконок: {e}")
        print("\nПопробуйте установить Pillow: pip install Pillow")

if __name__ == "__main__":
    create_icons()
