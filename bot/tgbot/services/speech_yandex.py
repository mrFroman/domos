import aiohttp
import os
import subprocess
import tempfile

from telethon import TelegramClient

from bot.tgbot.services.photo_yandex_gpt import *

from dotenv import load_dotenv
load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")


async def process_voice_with_yandex_telethon(message, client: TelegramClient, context: str = "") -> str:
    """
    Скачивает аудио из сообщения через Telethon и отправляет его в Yandex SpeechKit для распознавания.

    :param message: объект Telethon Message (с voice/audio)
    :param client: TelethonClient
    :param context: "lawyer" или "advert" — влияет на постобработку текста
    """
    # 1. Скачиваем и сохраняем файл через Telethon
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio_file:
        temp_audio_path = temp_audio_file.name
    await client.download_media(message, file=temp_audio_path)

    # 2. Проверка кодека через ffprobe
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", temp_audio_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        codec = result.stdout.strip()
        print(f"Определённый аудио-кодек: {codec}")
    except subprocess.CalledProcessError as e:
        print("Ошибка определения кодека:", e.stderr)
        raise Exception("Не удалось определить формат аудиофайла")

    # 3. Отправляем файл в Yandex SpeechKit
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}"
    }
    params = {
        "folderId": YANDEX_FOLDER_ID,
        "lang": "ru-RU",
        "format": "oggopus"
    }

    with open(temp_audio_path, "rb") as f:
        audio_binary = f.read()

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, params=params, data=audio_binary) as response:
            if response.status != 200:
                error = await response.text()
                raise Exception(f"Yandex SpeechKit error: {error}")

            result = await response.json()
            text = result.get("result", "")

    # 4. Постобработка текста через GPT
    if context == "advert":
        text = gpt_processor.format_text_for_advert(text)
    else:
        text = gpt_processor.format_text_for_lawyer(text)

    return text or "Не удалось распознать текст"


async def process_voice_with_yandex(voice_file_id: str, bot, context: str = "") -> str:
    voice_file = await bot.get_file(voice_file_id)
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{voice_file.file_path}"

    # 1. Скачиваем и сохраняем файл
    async with bot.session.get(file_url) as response:
        if response.status != 200:
            raise Exception(f"Ошибка загрузки файла: {response.status}")
        audio_content = await response.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio_file:
        temp_audio_file.write(audio_content)
        temp_audio_path = temp_audio_file.name

    # 2. Проверка кодека через ffprobe
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", temp_audio_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        codec = result.stdout.strip()
        print(f"Определённый аудио-кодек: {codec}")
    except subprocess.CalledProcessError as e:
        print("Ошибка определения кодека:", e.stderr)
        raise Exception("Не удалось определить формат аудиофайла")

    # 3. Отправляем файл как бинарные данные в Yandex SpeechKit
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}"
    }
    params = {
        "folderId": YANDEX_FOLDER_ID,
        "lang": "ru-RU",
        "format": "oggopus"
    }

    with open(temp_audio_path, "rb") as f:
        audio_binary = f.read()

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, params=params, data=audio_binary) as response:
            if response.status != 200:
                error = await response.text()
                raise Exception(f"Yandex SpeechKit error: {error}")

            result = await response.json()
            text = result.get("result", "")
    if context:
        text = gpt_processor.format_text_for_advert(text)
    else:
        text = gpt_processor.format_text_for_lawyer(text)
    if text:
        return text
    return "Не удалось распознать текст"
