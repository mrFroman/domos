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
    USEFULL_MESSAGES_DB_PATH = DATABASE_URL  # Для сообщений
else:
    # SQLite - используем файлы
    MAIN_DB_PATH = str(BASE_DIR / "bot" / "tgbot" / "databases" / "data.db")
    ADVERT_TOKENS_DB_PATH = str(BASE_DIR / "api" / "advert_tokens.db")
    CONTRACT_TOKENS_DB_PATH = str(BASE_DIR / "api" / "contract_tokens.db")
    AUDIO_DB_PATH = str(BASE_DIR / "bot" / "tgbot" / "databases" / "downloaded_audio.db")
    USEFULL_MESSAGES_DB_PATH = str(BASE_DIR / "bot" / "tgbot" / "databases" / "usefull_messages.db")

# Файл с позициями рекламы
ADVERT_POSITIONS_FILE = str(BASE_DIR / "api" / "advert_positions.json")

# Настройка логирования
# Создаем директорию для логов, если её нет
logs_dir = BASE_DIR / "logs"
logs_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(logs_dir / "app.log")),
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
