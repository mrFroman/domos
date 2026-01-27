import os
import pytz
import logging
from pathlib import Path
from dataclasses import dataclass
from environs import Env
from typing import List, Optional


# Максимальная длина сообщения бота
MAX_BOT_MSG_LENGTH = 4000

# Локальное время
YEKATERINBURG_TZ = pytz.timezone("Asia/Yekaterinburg")

# Базовый путь к проекту
BASE_DIR = Path(__file__).resolve().parents[0]

# Путь к файлу с позициями рекламы
ADVERT_POSITIONS_FILE = os.path.join(
    BASE_DIR,
    "bot",
    "tgbot",
    "databases",
    "advert_positions.json",
)

# Пути к базам данных
MAIN_DB_PATH = os.path.join(BASE_DIR, "bot", "tgbot", "databases", "data.db")
AUDIO_DB_PATH = os.path.join(
    BASE_DIR, "bot", "tgbot", "databases", "downloaded_audio.db"
)
USEFULL_MESSAGES_DB_PATH = os.path.join(
    BASE_DIR, "bot", "tgbot", "databases", "useful_messages.db"
)
VECTOR_DB_PATH = os.path.join(BASE_DIR, "bot", "tgbot", "vector_index")
ADVERT_TOKENS_DB_PATH = os.path.join(BASE_DIR, "api", "advert_tokens.db")
CONTRACT_TOKENS_DB_PATH = os.path.join(BASE_DIR, "api", "contract_tokens.db")

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

#Пути для логов
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Общий формат
formatter_bot = logging.Formatter("%(levelname)s: %(asctime)s - Bot: - %(message)s")
formatter_api = logging.Formatter("%(levelname)s: %(asctime)s - FastAPI: - %(message)s")

# Логгер для бота
logger_bot = logging.getLogger("bot")
logger_bot.setLevel(logging.INFO)

bot_file_handler = logging.FileHandler(LOG_DIR / "bot.log", encoding="utf-8")
bot_file_handler.setFormatter(formatter_bot)
bot_stream_handler = logging.StreamHandler()
bot_stream_handler.setFormatter(formatter_bot)

logger_bot.addHandler(bot_file_handler)
logger_bot.addHandler(bot_stream_handler)
logger_bot.propagate = False

# Логгер для FastAPI
logger_api = logging.getLogger("api")
logger_api.setLevel(logging.INFO)

api_file_handler = logging.FileHandler(LOG_DIR / "api.log", encoding="utf-8")
api_file_handler.setFormatter(formatter_api)
api_stream_handler = logging.StreamHandler()
api_stream_handler.setFormatter(formatter_api)

logger_api.addHandler(api_file_handler)
logger_api.addHandler(api_stream_handler)
logger_api.propagate = False


# Отключаем шумные библиотеки
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("telethon").setLevel(logging.WARNING)
logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)


@dataclass
class DbConfig:
    host: str
    password: str
    user: str
    database: str


@dataclass
class TgBot:
    token: str
    admin_ids: List[int]
    use_redis: bool


@dataclass
class TinkoffConfig:
    terminal_key: str
    password: str


@dataclass
class YandexGPTConfig:
    folder_id: str
    api_key: str
    temperature: float = 0.6
    max_tokens: int = 1000
    model_uri: str = "gpt://{folder_id}/yandexgpt-lite"
    api_url: str = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


@dataclass
class OpenAIClient:
    token: str


@dataclass
class Miscellaneous:
    other_params: Optional[str] = None


@dataclass
class Config:
    tg_bot: TgBot
    db: DbConfig
    tinkoff: TinkoffConfig
    yandex_gpt: YandexGPTConfig  # Вынесено на верхний уровень, как и другие конфиги
    open_ai: OpenAIClient
    misc: Miscellaneous


def load_config(path: str = None) -> Config:
    env = Env()
    env.read_env(path)

    yandex_gpt_config = YandexGPTConfig(
        folder_id=env.str("YANDEX_FOLDER_ID"),
        api_key=env.str("YANDEX_API_KEY"),
        temperature=env.float("YANDEX_GPT_TEMPERATURE", 0.6),
        max_tokens=env.int("YANDEX_GPT_MAX_TOKENS", 1000),
    )

    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN"),
            admin_ids=list(map(int, env.list("ADMINS"))),
            use_redis=env.bool("USE_REDIS"),
        ),
        db=DbConfig(
            host=env.str("DB_HOST"),
            password=env.str("DB_PASS"),
            user=env.str("DB_USER"),
            database=env.str("DB_NAME"),
        ),
        tinkoff=TinkoffConfig(
            terminal_key=env.str("TINKOFF_TERMINAL_KEY"),
            password=env.str("TINKOFF_PASSWORD"),
        ),
        yandex_gpt=yandex_gpt_config,  # Теперь на верхнем уровне конфига
        open_ai=OpenAIClient(token=env.str("OPENAI_API_KEY", "")),
        misc=Miscellaneous(other_params=env.str("OTHER_PARAMS", None)),
    )
