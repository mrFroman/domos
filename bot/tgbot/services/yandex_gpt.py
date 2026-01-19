import logging
import requests
from aiogram import types

from config import logger_bot


class YandexGPT:
    def __init__(self, folder_id: str, api_key: str):
        self.folder_id = folder_id
        self.api_key = api_key

    async def ask_yandex_gpt(self, prompt: str) -> str:

        headers = {
            'Authorization': f'Api-Key {self.api_key}',
            'Content-Type': 'application/json',
        }

        data = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": 0.3,
                "maxTokens": 1000
            },
            "messages": [
                {
                    "role": "user",
                    "text": prompt
                }
            ]
        }

        try:
            response = requests.post(
                'https://llm.api.cloud.yandex.net/foundationModels/v1/completion',
                headers=headers,
                json=data,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()['result']['alternatives'][0]['message']['text']
            else:
                logger_bot.error(
                    f"Yandex GPT error: {response.status_code} - {response.text}")
                return "Произошла ошибка при обработке запроса"

        except Exception as e:
            logger_bot.error(f"Yandex GPT exception: {str(e)}")
            return "Сервис временно недоступен, попробуйте позже"
