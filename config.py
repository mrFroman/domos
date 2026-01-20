"""
Конфигурационный файл для проекта Domos
Поддерживает как SQLite, так и PostgreSQL через переменную окружения DB_TYPE
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Загружаем переменные окружения
load_dotenv(find_dotenv())

# Базовый директорий проекта
BASE_DIR = Path(__file__).parent.absolute()

# Тип базы данных: sqlite или postgres
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

# Настройка путей к базам данных
if DB_TYPE == "postgres":
    # PostgreSQL - используем URL из переменных окружения
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    MAIN_DB_PATH = DATABASE_URL
    ADVERT_TOKENS_DB_PATH = DATABASE_URL
    CONTRACT_TOKENS_DB_PATH = DATABASE_URL
    AUDIO_DB_PATH = DATABASE_URL  # Для совместимости
else:
    # SQLite - используем файлы
    MAIN_DB_PATH = str(BASE_DIR / "bot" / "tgbot" / "databases" / "data.db")
    ADVERT_TOKENS_DB_PATH = str(BASE_DIR / "api" / "advert_tokens.db")
    CONTRACT_TOKENS_DB_PATH = str(BASE_DIR / "api" / "contract_tokens.db")
    AUDIO_DB_PATH = str(BASE_DIR / "bot" / "tgbot" / "databases" / "downloaded_audio.db")

# Файл с позициями рекламы
ADVERT_POSITIONS_FILE = str(BASE_DIR / "api" / "advert_positions.json")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(BASE_DIR / "logs" / "app.log")),
        logging.StreamHandler()
    ]
)

# Логгеры для разных модулей
logger_api = logging.getLogger("api")
logger_bot = logging.getLogger("bot")
logger_web = logging.getLogger("web")

# Функция для загрузки конфигурации (для совместимости со старым кодом)
def load_config(env_path=None):
    """Загружает конфигурацию из .env файла"""
    class Config:
        class TgBot:
            def __init__(self):
                self.token = os.getenv("BOT_TOKEN", "")
                self.use_redis = os.getenv("USE_REDIS", "False").lower() == "true"
        
        def __init__(self):
            self.tg_bot = self.TgBot()
    
    return Config()
