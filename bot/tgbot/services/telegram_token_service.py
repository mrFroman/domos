import logging
import sys
import os

from asgiref.sync import sync_to_async

from config import BASE_DIR

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Настраиваем Django перед импортом моделей
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.web.settings")
import django
django.setup()

from web.main_interface.models import TelegramToken


logger = logging.getLogger(__name__)


class TelegramTokenService:
    """Сервис для работы с токенами авторизации через Telegram"""

    @staticmethod
    async def mark_token_processed(token: str, telegram_user_id: int) -> bool:
        """Помечаем токен как обработанный ботом, если он ещё валиден"""

        def _process_token():
            telegram_token = TelegramToken.objects.filter(token=token).first()
            if not telegram_token:
                logger.warning(f"Токен не найден в БД: {token}")
                print(f"Сработало условие 1: Токен {token} не найден в БД")
                return False

            if telegram_token.is_expired():
                telegram_token.mark_expired()
                logger.warning(f"Токен истёк: {token}, создан: {telegram_token.created_at}")
                print(f"Сработало условие 2: Токен {token} истёк (создан: {telegram_token.created_at})")
                return False

            # Если токен уже обработан для этого же пользователя - это ОК
            if telegram_token.status == "processed":
                if telegram_token.telegram_user_id == telegram_user_id:
                    logger.info(f"Токен уже обработан для этого пользователя: {token}")
                    return True
                else:
                    logger.warning(f"Токен обработан для другого пользователя: {token}")
                    return False
            
            if telegram_token.status != "pending":
                logger.warning(f"Токен имеет неверный статус: {token}, статус: {telegram_token.status}")
                print(f"Сработало условие 3: Токен {token} имеет статус {telegram_token.status}, ожидается 'pending'")
                return False

            telegram_token.mark_processed(telegram_user_id)
            logger.info(f"Токен успешно обработан: {token}, user_id: {telegram_user_id}")
            print(f"Токен {token} успешно обработан для user_id: {telegram_user_id}")
            return True

        try:
            return await sync_to_async(_process_token, thread_sensitive=True)()
        except Exception:
            logger.exception(
                "Error marking token as processed: token=%s",
                token,
            )
            return False

    @staticmethod
    async def is_token_valid(token: str) -> bool:
        """Возвращает True, если токен существует и не истёк"""

        def _check():
            telegram_token = TelegramToken.objects.filter(token=token).first()
            if not telegram_token:
                return False
            if telegram_token.is_expired():
                telegram_token.mark_expired()
                return False
            return telegram_token.status in ["pending", "processed"]

        try:
            return await sync_to_async(_check, thread_sensitive=True)()
        except Exception:
            logger.exception("Error checking token validity: token=%s", token)
            return False

    @staticmethod
    async def get_token_status(token: str) -> str:
        """Возвращает текущий статус токена, независимо от срока действия"""

        def _status():
            telegram_token = TelegramToken.objects.filter(token=token).first()
            if not telegram_token:
                return "invalid"
            if telegram_token.is_expired():
                telegram_token.mark_expired()
                return "expired"
            return telegram_token.status

        try:
            return await sync_to_async(_status, thread_sensitive=True)()
        except Exception:
            logger.exception("Error getting token status: token=%s", token)
            return "error"
