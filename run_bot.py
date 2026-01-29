#!/usr/bin/env python
"""
Точка входа для запуска Telegram бота в Docker
"""
import sys
import os
import runpy

# Устанавливаем путь к корню проекта
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

# Запускаем бота как модуль
if __name__ == "__main__":
    # Выполняем bot/bot.py как скрипт с правильным sys.path
    bot_path = os.path.join(ROOT_DIR, "bot", "bot.py")
    exec(compile(open(bot_path).read(), bot_path, 'exec'))
