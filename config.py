import os
import pytz
import logging
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from dataclasses import dataclass, field
from typing import List, Optional
import pytz



# Максимальная длина сообщения бота
MAX_BOT_MSG_LENGTH = 4000

# Локальное время
YEKATERINBURG_TZ = pytz.timezone("Asia/Yekaterinburg")

# Базовый путь к проекту
BASE_DIR = Path(__file__).resolve().parents[0]

# Тип базы данных (sqlite или postgres)
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
    VECTOR_DB_PATH = str(BASE_DIR / "bot"/ "tgbot"/ "vector_index")
else:
    # SQLite - используем файлы
    MAIN_DB_PATH = str(BASE_DIR / "bot" / "tgbot" / "databases" / "data.db")
    ADVERT_TOKENS_DB_PATH = str(BASE_DIR / "api" / "advert_tokens.db")
    CONTRACT_TOKENS_DB_PATH = str(BASE_DIR / "api" / "contract_tokens.db")
    AUDIO_DB_PATH = str(BASE_DIR / "bot" / "tgbot" / "databases" / "downloaded_audio.db")
    USEFULL_MESSAGES_DB_PATH = str(BASE_DIR / "bot" / "tgbot" / "databases" / "usefull_messages.db")
    VECTOR_DB_PATH = str(BASE_DIR / "bot"/ "tgbot"/ "vector_index")

# Файл с позициями рекламы
ADVERT_POSITIONS_FILE = str(BASE_DIR / "api" / "advert_positions.json")

# Максимальная длина сообщения бота
MAX_BOT_MSG_LENGTH = 4000


# Локальное время
YEKATERINBURG_TZ = pytz.timezone("Asia/Yekaterinburg")

# Константы для работы с супергруппой
TOPIC_MAP = {
    "Старт продаж": 9,
    "Обучение": 2,
    "Акции": 3,
    "Скидки": 2306,
    "Новости": 434,
    "Повышенное вознаграждение": 2306,
    "Графики работ": 839,
    "Способы приобретения": 1271,
    "Мероприятия": 2124,
    "Розыгрыши": 2114,
    "Неразобранное": 1,
    "Контент": 114,
}
TOPIC_FIRST_MESSAGES = {
    "Старт продаж": 4487,
    "Обучение": 4488,
    "Акции": 4476,
    "Скидки": 4479,
    "Новости": 4481,
    "Повышенное вознаграждение": 4479,
    "Графики работ": 4482,
    "Способы приобретения": 4480,
    "Мероприятия": 4484,
    "Розыгрыши": 4483,
    "Неразобранное": 4489,
    "Контент": 4486,
}


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

formatter_bot = logging.Formatter("%(levelname)s: %(asctime)s - Bot: - %(message)s")
formatter_api = logging.Formatter("%(levelname)s: %(asctime)s - FastAPI: - %(message)s")


# Логгер для бота
logger_bot = logging.getLogger("bot")
logger_bot.setLevel(logging.INFO)

bot_file_handler = logging.FileHandler(logs_dir / "bot.log", encoding="utf-8")
bot_file_handler.setFormatter(formatter_bot)
bot_stream_handler = logging.StreamHandler()
bot_stream_handler.setFormatter(formatter_bot)

logger_bot.addHandler(bot_file_handler)
logger_bot.addHandler(bot_stream_handler)
logger_bot.propagate = False



# Логгер для FastAPI
logger_api = logging.getLogger("api")
logger_api.setLevel(logging.INFO)

api_file_handler = logging.FileHandler(logs_dir / "api.log", encoding="utf-8")
api_file_handler.setFormatter(formatter_api)
api_stream_handler = logging.StreamHandler()
api_stream_handler.setFormatter(formatter_api)

logger_api.addHandler(api_file_handler)
logger_api.addHandler(api_stream_handler)
logger_api.propagate = False


# Пути к базам данных (читаем из env для Docker, иначе локальные SQLite)
# MAIN_DB_PATH = os.getenv("MAIN_DB_PATH", os.path.join(BASE_DIR, "bot", "tgbot", "databases", "data.db"))
# AUDIO_DB_PATH = os.getenv("AUDIO_DB_PATH", os.path.join(BASE_DIR, "bot", "tgbot", "databases", "downloaded_audio.db"))
# USEFULL_MESSAGES_DB_PATH = os.getenv("USEFULL_MESSAGES_DB_PATH", os.path.join(BASE_DIR, "bot", "tgbot", "databases", "useful_messages.db"))
# VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", os.path.join(BASE_DIR, "bot", "tgbot", "vector_index"))
# ADVERT_TOKENS_DB_PATH = os.getenv("ADVERT_TOKENS_DB_PATH", os.path.join(BASE_DIR, "api", "advert_tokens.db"))
# CONTRACT_TOKENS_DB_PATH = os.getenv("CONTRACT_TOKENS_DB_PATH", os.path.join(BASE_DIR, "api", "contract_tokens.db"))

# Функция для загрузки конфигурации (для совместимости со старым кодом)
def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes", "on")


def env_list_int(name: str, default: Optional[List[int]] = None) -> List[int]:
    value = os.getenv(name)
    if not value:
        return default or []
    return [int(x) for x in value.split(",")]


@dataclass
class TgBotConfig:
    token: str = ""
    admin_ids: List[int] = field(default_factory=list)
    use_redis: bool = False


@dataclass
class DbConfig:
    host: str = ""
    password: str = ""
    user: str = ""
    database: str = ""


@dataclass
class YandexGPTConfig:
    folder_id: str = ""
    api_key: str = ""
    temperature: float = 0.6
    max_tokens: int = 1000


@dataclass
class OpenAIConfig:
    token: str = ""


@dataclass
class MiscConfig:
    other_params: Optional[str] = None


@dataclass
class Config:
    tg_bot: TgBotConfig
    db: DbConfig
    yandex_gpt: YandexGPTConfig
    open_ai: OpenAIConfig
    misc: MiscConfig



def load_config(env_path=None) -> Config:
     return Config(
        tg_bot=TgBotConfig(
            token=os.getenv("BOT_TOKEN", ""),
            admin_ids=env_list_int("ADMINS"),
            use_redis=env_bool("USE_REDIS"),
        ),
        db=DbConfig(
            host=os.getenv("DB_HOST", ""),
            password=os.getenv("DB_PASS", ""),
            user=os.getenv("DB_USER", ""),
            database=os.getenv("DB_NAME", ""),
        ),
        yandex_gpt=YandexGPTConfig(
            folder_id=os.getenv("YANDEX_FOLDER_ID", ""),
            api_key=os.getenv("YANDEX_API_KEY", ""),
            temperature=float(os.getenv("YANDEX_GPT_TEMPERATURE", 0.6)),
            max_tokens=int(os.getenv("YANDEX_GPT_MAX_TOKENS", 1000)),
        ),
        open_ai=OpenAIConfig(
            token=os.getenv("OPENAI_API_KEY", ""),
        ),
        misc=MiscConfig(
            other_params=os.getenv("OTHER_PARAMS"),
        ),
    )


# def load_config(env_path=None):
#     """Загружает конфигурацию из .env файла"""
#     class Config:
#         class TgBot:
#             def __init__(self):
#                 self.token = os.getenv("BOT_TOKEN", "")
#                 self.use_redis = os.getenv("USE_REDIS", "False").lower() == "true"
        
#         def __init__(self):
#             self.tg_bot = self.TgBot()
    
#     return Config()
