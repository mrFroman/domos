import os
import requests
import hashlib
import json
from config import load_config
from pathlib import Path

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

path = str(Path(__file__).parents[2])
Config = load_config(f"{path}/.env")


class TinkoffPayment:
    @staticmethod
    def generate_token(data: dict) -> str:
        """Генерация токена для подписи запроса"""
        data_to_sign = {
            k: v for k, v in data.items() if k != "Receipt"
        }  # Receipt отдельно
        data_to_sign["Password"] = Config.tinkoff.password
        values = [str(value) for key, value in sorted(data_to_sign.items())]
        concatenated = "".join(values)
        return hashlib.sha256(concatenated.encode("utf-8")).hexdigest()

    @staticmethod
    def initial_recurrent_payment(
        amount: int,
        order_id: str,
        description: str,
        customer_key: str,
    ) -> dict:
        """Инициализация рекуррентного платежа"""
        url = "https://securepay.tinkoff.ru/v2/Init"

        payload = {
            "TerminalKey": Config.tinkoff.terminal_key,
            "Amount": amount * 100,
            "OrderId": order_id,
            "Description": description,
            "CustomerKey": customer_key,
            "SuccessURL": "https://t.me/DomosproBot",
            "FailURL": "https://t.me/DomosproBot",
            # TODO Изменить урл на сервере
            "NotificationURL": "https://neurochief.pro/api/tinkoff_recurrent_payment_webhook/",
            # "NotificationURL": "https://indiscreetly-overruling-mako.cloudpub.ru/tinkoff_recurrent_payment_webhook/",
            "PayType": "O",
            "Recurrent": "Y",
            "DATA": {
                "OperationInitiatorType": "1",
            },
            "Receipt": {
                "Email": "customer@example.com",
                "Taxation": "patent",
                "Items": [
                    {
                        "Name": description,
                        "Price": amount * 100,
                        "Quantity": 1,
                        "Amount": amount * 100,
                        "Tax": "none",
                    }
                ],
            },
        }

        # Генерация токена
        token_data = payload.copy()
        token_data.pop(
            "Receipt"
        )  # Tinkoff требует, чтобы Receipt не участвовал в подписи
        token_data.pop("DATA")  # Tinkoff требует, чтобы DATA не участвовал в подписи
        payload["Token"] = TinkoffPayment.generate_token(token_data)

        headers = {"Content-Type": "application/json"}

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        return response.json()

    @staticmethod
    def init_repeat_recurrent_payment(
        order_id: str,
        description: str,
    ) -> dict:
        """Инициализация повторного рекуррентного платежа"""
        url = "https://securepay.tinkoff.ru/v2/Init"

        payload = {
            "TerminalKey": Config.tinkoff.terminal_key,
            "Amount": int(os.getenv("MOUNTH_SUBSCRIPTION_PRICE")) * 100,
            "OrderId": order_id,
            "Description": description,
            # TODO Изменить урл на сервере
            "NotificationURL": "https://neurochief.pro/api/tinkoff_repeat_recurrent_payment_webhook/",
            # "NotificationURL": "https://indiscreetly-overruling-mako.cloudpub.ru/tinkoff_repeat_recurrent_payment_webhook/",
            "DATA": {
                "OperationInitiatorType": "R",
            },
            "Receipt": {
                "Email": "customer@example.com",
                "Taxation": "patent",
                "Items": [
                    {
                        "Name": description,
                        "Price": int(os.getenv("MOUNTH_SUBSCRIPTION_PRICE")) * 100,
                        "Quantity": 1,
                        "Amount": int(os.getenv("MOUNTH_SUBSCRIPTION_PRICE")) * 100,
                        "Tax": "none",
                    }
                ],
            },
        }

        # Генерация токена
        token_data = payload.copy()
        token_data.pop("Receipt")
        token_data.pop("DATA")
        payload["Token"] = TinkoffPayment.generate_token(token_data)

        headers = {"Content-Type": "application/json"}

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        return response.json()

    @staticmethod
    def charge_recurrent_payment(payment_id, rebill_id):
        """Проведение повторного рекуррентного платежа"""
        url = "https://securepay.tinkoff.ru/v2/Charge"

        payload = {
            "TerminalKey": Config.tinkoff.terminal_key,
            "PaymentId": payment_id,
            "RebillId": rebill_id,
        }
        token_data = payload.copy()
        payload["Token"] = TinkoffPayment.generate_token(token_data)

        headers = {"Content-Type": "application/json"}

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        return response.json()

    @staticmethod
    def init_payment(
        amount: int,
        order_id: str,
        description: str,
        customer_key: str,
    ) -> dict:
        """Инициализация платежа"""
        url = "https://securepay.tinkoff.ru/v2/Init"

        payload = {
            "TerminalKey": Config.tinkoff.terminal_key,
            "Amount": amount * 100,
            "OrderId": order_id,
            "Description": description,
            "CustomerKey": customer_key,
            "SuccessURL": "https://t.me/DomosproBot",
            "FailURL": "https://t.me/DomosproBot",
            "PayType": "O",
            "Receipt": {
                "Email": "customer@example.com",
                "Taxation": "patent",
                "Items": [
                    {
                        "Name": description,
                        "Price": amount * 100,
                        "Quantity": 1,
                        "Amount": amount * 100,
                        "Tax": "none",
                    }
                ],
            },
        }

        # Генерация токена
        token_data = payload.copy()
        token_data.pop(
            "Receipt"
        )  # Tinkoff требует, чтобы Receipt не участвовал в подписи
        payload["Token"] = TinkoffPayment.generate_token(token_data)

        headers = {"Content-Type": "application/json"}

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        return response.json()

    @staticmethod
    def check_payment_status(payment_id: str) -> dict:
        """Проверка статуса платежа"""
        url = "https://securepay.tinkoff.ru/v2/GetState"

        payload = {
            "TerminalKey": Config.tinkoff.terminal_key,
            "PaymentId": payment_id,
        }

        payload["Token"] = TinkoffPayment.generate_token(payload)

        headers = {
            "Content-Type": "application/json",
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        return response.json()
