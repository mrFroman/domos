import requests
import base64
import logging
from typing import Dict, Optional
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.utils import executor
import tempfile
import os
import json
import time
from PIL import Image
import re
from PIL import Image, ImageEnhance, ImageFilter
import tempfile
from dotenv import load_dotenv
load_dotenv()
# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YandexVisionAPI:
    def __init__(self, api_key: str, folder_id: str):
        self.api_key = api_key
        self.folder_id = folder_id
        self.vision_url = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"
        # self.vision_url = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"

    def _encode_image_to_base64(self, image_path: str) -> str:
        """Конвертирует изображение в base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def extract_text_from_image(self, image_path: str, model) -> Optional[str]:
        """Распознает текст и извлекает данные паспорта из машиночитаемой зоны"""
        # Распознаем текст с изображения
        raw_text = self._extract_text(image_path, model)
        if not raw_text:
            return None
        return raw_text

    def _extract_text(self, image_path: str, model_type: str = "handwritten") -> Optional[str]:
        """Функция распознавания текста с поддержкой рукописного ввода

        Args:
            image_path: Путь к изображению
            model_type: Тип распознавания ('handwritten' для рукописного текста)
        """
        # Определяем тип файла
        is_pdf = image_path.lower().endswith('.pdf')

        # Для PDF всегда используем OCR API
        if is_pdf or model_type == "handwritten":
            headers = {
                "Authorization": f"Api-Key {self.api_key}",
                "Content-Type": "application/json",
                "x-data-logging-enabled": "true"  # Для отладки в Яндекс.Cloud
            }

            # Кодируем изображение в Base64
            content = self._encode_image_to_base64(image_path)

            # Определяем MIME-тип автоматически
            mime_type = "image/jpeg"  # По умолчанию
            if image_path.lower().endswith('.png'):
                mime_type = "image/png"
            elif image_path.lower().endswith('.pdf'):
                mime_type = "application/pdf"

            payload = {
                "mimeType": mime_type,
                "languageCodes": ["ru"],  # Только русский для паспортов
                "model": model_type,      # Указываем модель распознавания
                "content": content
            }

            try:
                # Используем правильный endpoint для OCR API
                ocr_url = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"

                response = requests.post(
                    ocr_url,
                    headers=headers,
                    json=payload,
                    timeout=30  # Увеличенный таймаут для рукописного текста
                )

                response.raise_for_status()
                result = response.json()

                # Собираем все распознанные слова
                text_parts = []
                if 'result' in result and 'textAnnotation' in result['result']:
                    for block in result['result']['textAnnotation']['blocks']:
                        for line in block['lines']:
                            for word in line['words']:
                                text_parts.append(word['text'])

                return " ".join(text_parts) if text_parts else None

            except requests.exceptions.RequestException as e:
                logger.error(f"Yandex OCR API request failed: {str(e)}")
                if hasattr(e, 'response'):
                    logger.error(f"Response content: {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return None
        else:
            headers = {
                "Authorization": f"Api-Key {self.api_key}",
                "Content-Type": "application/json",
            }

            # Конфигурация в зависимости от типа модели
            feature = {
                "type": "TEXT_DETECTION",  # Всегда TEXT_DETECTION!
                "text_detection_config": {
                    "language_codes": ["ru"],
                    "model": model_type  # Здесь указываем конкретную модель
                }
            }

            payload = {
                "folderId": self.folder_id,
                "analyze_specs": [{
                    "content": self._encode_image_to_base64(image_path),
                    "features": [feature]
                }]
            }

            try:
                response = requests.post(
                    self.vision_url, headers=headers, json=payload, timeout=20)
                response.raise_for_status()
                result = response.json()
                text_parts = []

                if result.get('results'):
                    for result_item in result['results'][0]['results']:
                        if 'textDetection' in result_item:
                            for page in result_item['textDetection']['pages']:
                                for block in page['blocks']:
                                    for line in block['lines']:
                                        for word in line['words']:
                                            text_parts.append(word['text'])
                return " ".join(text_parts) if text_parts else None

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {str(e)}")
                if hasattr(e, 'response'):
                    logger.error(f"Response: {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Processing error: {str(e)}")
                return None

    def extract_passport_number(self, raw_text: str) -> Dict[str, str]:
        """Извлекает серию и номер паспорта после удаления всех пробелов"""
        import re

        # Удаляем ВСЕ пробелы из текста для надежного поиска
        clean_text = re.sub(r'\s+', '', raw_text)

        # Ищем первую последовательность: минимум 3 '<' и 10 цифр
        first_match = re.search(r'<{3,}(\d{3})(\d{6})(\d)', clean_text)
        if not first_match:
            return {}

        first_part = first_match.group(1)  # Первые 3 цифры (652)
        number_part = first_match.group(2)  # Основные 6 цифр номера (077682)
        _ = first_match.group(3)  # Лишняя цифра (игнорируем)

        # Ищем вторую последовательность: минимум 3 '<' и цифра
        second_match = re.search(r'<{3,}(\d)', clean_text[first_match.end():])
        if not second_match:
            return {}

        last_digit = second_match.group(1)  # Четвертая цифра серии (4)

        return {
            "series": f"{first_part}{last_digit}",  # 652 + 4 = 6524
            "number": number_part,  # 077682
            # 6524 077682
            "full_number": f"{first_part}{last_digit} {number_part}"
        }

    def _remove_mrz_from_text(self, text: str) -> str:
        """Удаляет машиночитаемую зону из текста"""
        import re
        # Удаляем строки с множеством '<' и букв/цифр
        return re.sub(r'[A-Z0-9<]{25,}', '', text).strip()


class YandexGPT:
    def __init__(self, api_key: str, folder_id: str):
        self.api_key = api_key
        self.folder_id = folder_id
        self.gpt_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    def extract_passport_data(self, raw_text: str) -> Dict[str, str]:
        """Извлекает данные паспорта с обработкой форматирования"""
        system_prompt = """
        Ты — ассистент для строгого преобразования данных паспорта РФ в JSON. Внимание на особые правила:

        1. СТРОГИЙ ПОРЯДОК ДАННЫХ:
        [Гражданство] [Пол] [Кем выдан] [Дата выдачи] [Код подразделения] [ФИО] [Дата рождения] [Место рождения] [Серия/номер]

        2. ПРАВИЛА ИЗВЛЕЧЕНИЯ:
        - Серия/номер: последние 10 цифр → первые 4 цифры + пробел + остальные 6 ("XXXX XXXXXX")
        - Код подразделения: 6 цифр С ДЕФИСОМ в формате "XXX-XXX" ПЕРЕД ФИО
        - Дата после кода подразделения → дата выдачи
        - Дата после пола и перед местом рождения → дата рождения
        - Текст между гражданством и датой выдачи → кем выдан
        - Текст после даты рождения до серии/номера → место рождения
        - Последние 3 слова перед датой рождения → ФИО (Фамилия Имя Отчество)

        3. КРИТИЧЕСКИЕ ПРАВИЛА:
        - Код подразделения ВСЕГДА содержит дефис: "XXX-XXX"
        - Серия/номер ВСЕГДА последние 10 цифр без дефисов
        - Дата рождения ВСЕГДА < даты выдачи

        Пример правильного вывода для:
        \"rus - муж увд г. кургана 06.08.2003 451-001 белешев константин александрович 22.11.1969 гор.курган 3703833248\"

        {
        \"last_name\": \"Белешев\",
        \"first_name\": \"Константин\",
        \"middle_name\": \"Александрович\",
        \"passport_number\": \"3703 833248\",
        \"birth_date\": \"22.11.1969\",
        \"birth_place\": \"гор.курган\",
        \"issued_by\": \"увд г. кургана\",
        \"issue_date\": \"06.08.2003\",
        \"department_code\": \"451-001\"
        }

        Если не хватает данных для заполнения поля, заполни его пустой строкой. Верни ТОЛЬКО JSON без комментариев. Если данные не соответствуют шаблону - верни пустой объект. 
        """

        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": 0.3,
                "maxTokens": 1000
            },
            "messages": [
                {
                    "role": "system",
                    "text": system_prompt
                },
                {
                    "role": "user",
                    "text": f"Извлеки данные из этого текста:\n{raw_text[:3000]}"
                }
            ]
        }

        try:
            with requests.Session() as session:
                response = session.post(
                    self.gpt_url,
                    headers=headers,
                    json=payload,
                    timeout=(10, 60))

                response.raise_for_status()
                result = response.json()
                gpt_response = result['result']['alternatives'][0]['message']['text']

                # Очистка ответа от лишних символов
                cleaned_response = self._clean_gpt_response(gpt_response)
                try:
                    return json.loads(cleaned_response)
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Не удалось распарсить ответ как JSON. Очищенный ответ: {cleaned_response}")
                    logger.error(f"Оригинальный ответ: {gpt_response}")
                    return {}

        except Exception as e:
            logger.error(f"Ошибка при запросе к Yandex GPT: {str(e)}")
            return {}

    def extract_registration_data(self, raw_text: str) -> Dict[str, str]:
        """Извлекает данные регистрации, гарантируя валидный JSON в ответе"""
        DEFAULT_RESPONSE = {
            "registration_adress": "Свердловская обл"
        }

        system_prompt = """
        Ты — ассистент для извлечения адреса регистрации из паспорта РФ. 
        Если адрес нечеткий, используй открытые источники для уточнения (предположительно Свердловская область).
        Верни ТОЛЬКО JSON формата:
        {"registration_address": "ОБЛ СВЕРДЛОВСКАЯ, Г ERATEPИНБУРГ УЛ МРАМОРСКАЯ, Д. 4/2, KB- 384"}
        Если адрес невозможно определить, верни {"registration_address": "Свердловская обл"}
        """

        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": 0.1,
                "maxTokens": 1000
            },
            "messages": [
                {
                    "role": "system",
                    "text": system_prompt
                },
                {
                    "role": "user",
                    "text": f"Извлеки адрес регистрации:\n{raw_text[:3000]}"
                }
            ]
        }

        try:
            with requests.Session() as session:
                response = session.post(
                    self.gpt_url,
                    headers=headers,
                    json=payload,
                    timeout=(10, 60))

                response.raise_for_status()
                result = response.json()
                gpt_response = result['result']['alternatives'][0]['message']['text']

                # Очистка и парсинг ответа
                cleaned_response = self._clean_gpt_response(gpt_response)

                try:
                    parsed = json.loads(cleaned_response)
                    # Проверяем наличие обязательного поля
                    if "registration_adress" in parsed or "registration_address" in parsed:
                        # Нормализуем ключ (на случай опечаток)
                        address = parsed.get("registration_adress") or parsed.get(
                            "registration_address")
                        return {"registration_adress": address}
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.error(
                        f"Ошибка парсинга JSON: {str(e)}. Ответ: {cleaned_response}")

        except Exception as e:
            logger.error(f"Ошибка при запросе к Yandex GPT: {str(e)}")

        # Возвращаем значение по умолчанию в случае любых ошибок
        return DEFAULT_RESPONSE

    def format_text_for_lawyer(self, raw_text: str) -> str:
        """Форматирует текст, расставляя знаки препинания и делая его читаемым для юриста без потери информации"""

        system_prompt = """
        Ты — профессиональный помощник юриста. Твоя задача — сделать текст читаемым: расставь знаки препинания, разбей на предложения, оформи его как нормальный юридический текст.
        Нельзя убирать или добавлять смысл — только улучшай читаемость.
        Пример: "я иванов иван иванович родился в 1982 году проживаю по адресу город москва улица советская дом 10" ->
        "Я, Иванов Иван Иванович, родился в 1982 году. Проживаю по адресу: город Москва, улица Советская, дом 10."
        """

        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": 0.2,
                "maxTokens": 1000
            },
            "messages": [
                {
                    "role": "system",
                    "text": system_prompt
                },
                {
                    "role": "user",
                    "text": f"Приведи текст в читаемый для юриста вид:\n{raw_text[:3000]}"
                }
            ]
        }

        try:
            with requests.Session() as session:
                response = session.post(
                    self.gpt_url,
                    headers=headers,
                    json=payload,
                    timeout=(10, 60)
                )
                response.raise_for_status()
                result = response.json()
                formatted_text = result['result']['alternatives'][0]['message']['text']
                return formatted_text.strip()
        except Exception as e:
            logger.error(
                f"Ошибка при форматировании текста для юриста: {str(e)}")
            return raw_text  # Возвращаем исходный текст в случае ошибки

    def format_text_for_advert(self, raw_text: str) -> str:
        """Форматирует текст, расставляя знаки препинания и делая его читаемым для юриста без потери информации"""

        system_prompt = """
        Ты — профессиональный помощник по рекламе. Твоя задача — сделать текст более привлекательным и читаемым: расставь знаки препинания, разбей на предложения, оформи его как нормальный рекламный текст. Нельзя убирать или добавлять смысл — только улучшай читаемость и придавай тексту более яркий и привлекательный вид. Пример: "я иванов иван иванович родился в 1982 году проживаю по адресу город москва улица советская дом 10" -> "Я, Иванов Иван Иванович, родился в 1982 году. Проживаю по адресу: город Москва, улица Советская, дом 10."
        """

        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": 0.2,
                "maxTokens": 1000
            },
            "messages": [
                {
                    "role": "system",
                    "text": system_prompt
                },
                {
                    "role": "user",
                    "text": f"Приведи текст в читаемый для юриста вид:\n{raw_text[:3000]}"
                }
            ]
        }

        try:
            with requests.Session() as session:
                response = session.post(
                    self.gpt_url,
                    headers=headers,
                    json=payload,
                    timeout=(10, 60)
                )
                response.raise_for_status()
                result = response.json()
                formatted_text = result['result']['alternatives'][0]['message']['text']
                return formatted_text.strip()
        except Exception as e:
            logger.error(
                f"Ошибка при форматировании текста для юриста: {str(e)}")
            return raw_text  # Возвращаем исходный текст в случае ошибки

    def _clean_gpt_response(self, response: str) -> str:
        """Очищает ответ GPT от лишнего форматирования"""
        # Удаляем обратные кавычки и маркеры кода
        response = response.replace('```json', '').replace('```', '').strip()

        # Удаляем все до первой { и после последней }
        start = response.find('{')
        end = response.rfind('}') + 1

        if start != -1 and end != 0:
            return response[start:end]
        return response

# Инициализация бота


def parse_corrected_data(original: str, corrected: str) -> dict:
    """Сравнивает оригинальное и исправленное сообщение и возвращает изменения"""

    original_lines = [line.strip()
                      for line in original.strip().split('\n') if line.strip()]
    corrected_lines = [line.strip()
                       for line in corrected.strip().split('\n') if line.strip()]
    if len(original_lines) != len(corrected_lines):
        raise ValueError(
            "Количество строк в сообщении изменилось. Можно менять только значения после двоеточий.")
    # Четко указываем номера строк, которые содержат данные
    field_mapping = {
        'rieltor': {
            1: 'last_name',
            2: 'passport_data',
            3: 'birth_date',
            4: 'birth_place',
            5: 'issued_by',
            6: 'issue_date',
            7: 'department_code',
            8: 'registration_address'
        },
        'client': {
            10: 'last_name',
            11: 'passport_data',
            12: 'birth_date',
            13: 'birth_place',
            14: 'issued_by',
            15: 'issue_date',
            16: 'department_code',
            17: 'registration_address'
        }
    }

    changes = {'rieltor': {}, 'client': {}}

    for role in ['rieltor', 'client']:
        for line_num, field in field_mapping[role].items():
            orig_line = original_lines[line_num].strip()
            corr_line = corrected_lines[line_num].strip()

            # Проверка, что структура строки не нарушена
            if ':' not in orig_line or ':' not in corr_line:
                raise ValueError(
                    f"Нарушена структура строки №{line_num + 1}: отсутствует ':'")

            orig_prefix, orig_value = orig_line.split(':', 1)
            corr_prefix, corr_value = corr_line.split(':', 1)

            if orig_prefix.strip() != corr_prefix.strip():
                raise ValueError(
                    f"Нельзя изменять часть перед двоеточием. Ошибка в строке:\n{corr_line}")

            orig_value = orig_value.strip()
            corr_value = corr_value.strip()

            if field == 'passport_data':
                # Надёжно извлекаем два последних числовых блока
                orig_parts = orig_value.strip().split()
                corr_parts = corr_value.strip().split()

                if len(orig_parts) < 2 or len(corr_parts) < 2:
                    raise ValueError(
                        "Слишком мало данных для серии и номера паспорта")

                orig_series, orig_number = orig_parts[-2], orig_parts[-1]
                corr_series, corr_number = corr_parts[-2], corr_parts[-1]

                if orig_series != corr_series:
                    changes[role]['passport_series'] = (
                        orig_series, corr_series)
                if orig_number != corr_number:
                    changes[role]['passport_number'] = (
                        orig_number, corr_number)
            else:
                if orig_value != corr_value:
                    changes[role][field] = (orig_value, corr_value)
    return changes


# Инициализация API
vision_api = YandexVisionAPI(
    api_key=os.getenv("YANDEX_VISION_API_KEY", ""), folder_id=os.getenv("YANDEX_FOLDER_ID", ""))
gpt_processor = YandexGPT(
    api_key=os.getenv("YANDEX_GPT_API_KEY", ""), folder_id=os.getenv("YANDEX_FOLDER_ID", ""))
