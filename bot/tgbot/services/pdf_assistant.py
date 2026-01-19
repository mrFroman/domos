import os
import pathlib
import logging
import requests
from yandex_cloud_ml_sdk import YCloudML
from yandex_cloud_ml_sdk.search_indexes import (
    TextSearchIndexType,
    StaticIndexChunkingStrategy,
)

from typing import Dict, Any
path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)

class PDFAssistant:
    def __init__(self, folder_id: str, api_key: str, docs_folder=f"{path}/converted_docs"):
        self.sdk = YCloudML(folder_id=folder_id, auth=api_key)
        self.folder_id = folder_id
        self.api_key = api_key
        self.docs_folder = docs_folder
        self.assistant = None
        self.index = None
        self._initialized = False
        self.files = []
        # Хранилище для потоков разных пользователей
        self.user_threads: Dict[str, Any] = {}  # {user_id: thread}
        
        # Инструкция для ассистента
        self.assistant_instruction = """
        Ты - профессиональный ассистент Domosclub. 
        отвечай из своих знаний на любой вопрос информациии о котором нет в документе.
        """
        # Также в ответе указывай источник, откуда ты взял информацию.
        # Источником могут быть ТОЛЬКО:
        # 1. Внутреняя база знаний
        # 2. Сайт

        # Формат ответа:
        # <Ответ на вопрос пользователя>.
        # Источник: <Откуда ты взял информацию>

    def create_index(self):
        """Создаёт текстовый индекс из всех Markdown-файлов в папке."""
        md_files = [
            os.path.join(root, fn)
            for root, _, files in os.walk(self.docs_folder)
            for fn in files
            if fn.lower().endswith(".md")
        ]

        if not md_files:
            raise RuntimeError("Нет Markdown-файлов для индексации.")

        logger.info(f"Загружаем {len(md_files)} Markdown-файлов...")
        self.files = [self.sdk.files.upload(path, ttl_days=5, expiration_policy="static") for path in md_files]

        logger.info("Создаём индекс...")
        op = self.sdk.search_indexes.create_deferred(
            self.files,
            index_type=TextSearchIndexType(
                chunking_strategy=StaticIndexChunkingStrategy(
                    max_chunk_size_tokens=2048,
                    chunk_overlap_tokens=700,
                ),
            ),
        )

        self.index = op.wait()
        logger.info("Индекс создан.")

    def initialize_assistant(self):
        """Инициализирует ассистента с индексом."""
        if self.index is None:
            raise RuntimeError("Сначала вызовите create_index().")

        tool = self.sdk.tools.search_index(self.index)
        self.assistant = self.sdk.assistants.create(
            "yandexgpt", 
            tools=[tool],
            instruction=self.assistant_instruction
        )
        self._initialized = True
        logger.info("Ассистент инициализирован.")

    def get_or_create_thread(self, user_id: str):
        """Возвращает или создает поток для конкретного пользователя."""
        if user_id not in self.user_threads:
            self.user_threads[user_id] = self.sdk.threads.create()
            logger.info(f"Создан новый поток для пользователя {user_id}")
        return self.user_threads[user_id]

    # def ask_yandex_gpt(self, prompt: str, user_id: str) -> str:
    #     """Задает вопрос ассистенту и возвращает ответ с учетом истории пользователя."""
    #     if not prompt.strip():
    #         return "❗ Пожалуйста, задайте непустой вопрос."

    #     if not self._initialized:
    #         self.create_index()
    #         self.initialize_assistant()

    #     # Получаем поток для конкретного пользователя
    #     thread = self.get_or_create_thread(user_id)
    #     thread.write(prompt)
        
    #     run = self.assistant.run(thread)
    #     result = run.wait()

    #     # Форматируем ответ с указанием источника
    #     response = result.text
        
        
    #     return response

    def __format_sources(self, result) -> str:
        """
        Преобразует источники из ответа YandexGPT в читаемый текст.
        """
        if not getattr(result, "citations", None):
            return ""

        lines = ["\n\n📚 Источники:"]
        for i, citation in enumerate(result.citations, start=1):
            for source in citation.sources:
                # Берём текстовый фрагмент
                # print(f'{source=}')
                chunk_text = ""
                if hasattr(source, "parts"):
                    chunk_text = " ".join(source.parts).strip()

                # Берём файл, если есть
                file_name = getattr(getattr(source, "file", None), "name", None)
                file_id = getattr(getattr(source, "file", None), "id", None)

                preview = chunk_text[:200].replace("\n", " ") + ("..." if len(chunk_text) > 200 else "")

                if file_name:
                    lines.append(f"- [{file_name}] {preview}")
                elif file_id:
                    lines.append(f"- 📄 Файл {file_id}: {preview}")
                else:
                    lines.append(f"- {preview}")

        return "\n".join(lines)


    def ask_yandex_gpt(self, prompt: str, user_id: str) -> str:
        """Задает вопрос ассистенту и возвращает ответ с учетом истории пользователя + источники."""

        if not prompt.strip():
            return "❗ Пожалуйста, задайте непустой вопрос."

        if not self._initialized:
            self.create_index()
            self.initialize_assistant()

        # Получаем поток для конкретного пользователя
        thread = self.get_or_create_thread(user_id)
        thread.write(prompt)

        run = self.assistant.run(thread)
        result = run.wait()

        # print(f'{result=}')

        # Основной ответ
        response = result.text
        sources_text = self.__format_sources(result)

        # print(f'{sources_text=}')


        return response



    def cleanup_user(self, user_id: str):
        """Очищает историю конкретного пользователя."""
        if user_id in self.user_threads:
            self.user_threads[user_id].delete()
            del self.user_threads[user_id]
            logger.info(f"История пользователя {user_id} очищена")

    def cleanup(self):
        """Удаляет ассистента, индекс, поток и файлы."""
        if self.assistant:
            self.assistant.delete()
        if self.index:
            self.index.delete()
        for f in self.files:
            f.delete()
        for thread in self.user_threads.values():
            thread.delete()
        self.user_threads.clear()
        logger.info("Полная очистка завершена.")