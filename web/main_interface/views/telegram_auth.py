import logging
import os

from django.contrib.auth import login as django_login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.http import JsonResponse

from dotenv import load_dotenv, find_dotenv
from web.main_interface.models import TelegramToken


load_dotenv(find_dotenv())
BOT_USERNAME = os.getenv("BOT_USERNAME", "test_neuroochief_bot")
logger = logging.getLogger(__name__)


def _expire_previous_session_token(request):
    """Удаляем предыдущий токен авторизации из сессии и БД"""
    previous_token = request.session.pop("telegram_login_token", None)
    if previous_token:
        TelegramToken.expire_token(previous_token)
        logger.debug(
            "Старый токен авторизации помечен как истекший: token=%s",
            previous_token,
        )


def login(request):
    """Генерируем ссылку для входа через бота"""
    # Редиректим только если пользователь полностью авторизован (есть telegram_id в сессии)
    if request.user.is_authenticated and request.session.get("telegram_id"):
        return redirect("main_menu")

    _expire_previous_session_token(request)
    # Создаем новый токен в БД
    telegram_token = TelegramToken.create_token()
    print(
        f"Создан новый telegram токен для входа: {telegram_token.token}",
    )
    request.session["telegram_login_token"] = telegram_token.token
    telegram_link = f"https://t.me/{BOT_USERNAME}?start={telegram_token.token}"
    print(
        "Telegram login link сгенерирован: link=%s session_token=%s",
        telegram_link,
        request.session["telegram_login_token"],
    )
    return render(
        request,
        "auth/telegram_login.html",
        {
            "telegram_link": telegram_link,
            "telegram_token": telegram_token.token,
        },
    )


def telegram_auth_callback(request):
    """Обрабатываем callback после того как бот положил токен"""
    token = request.GET.get("token")
    print(
        "Обработка callback авторизации через Telegram: token=%s",
        token,
    )

    if not token:
        print("Callback получен без токена, выполняем редирект")
        return redirect("telegram_login_redirect")

    # Получаем токен из БД
    telegram_token = TelegramToken.get_valid_token(token)
    if not telegram_token or telegram_token.status != "processed":
        print(
            "Некорректный токен авторизации: token=%s status=%s",
            token,
            telegram_token.status if telegram_token else "not found",
        )
        return redirect("telegram_login_redirect")

    # Отмечаем токен как использованный
    telegram_token.mark_used()
    print(
        "Токен помечен как использованный: token=%s telegram_user_id=%s",
        token,
        telegram_token.telegram_user_id,
    )

    # Сохраняем telegram_id в сессии для дальнейшей работы в вью-функциях
    request.session["telegram_id"] = int(telegram_token.telegram_user_id)
    print(
        f'Telegram ID сохранен в сессии: {request.session["telegram_id"]}',
    )

    # Создаем или получаем пользователя Django и логиним
    user, _ = User.objects.get_or_create(
        username=f"tg_{telegram_token.telegram_user_id}"
    )
    print(
        "Пользователь авторизован через Telegram: username=%s",
        user.username,
    )
    django_login(request, user)
    return redirect("main_menu")


def check_telegram_token(request):
    """Проверяем статус токена"""
    token = request.GET.get("token")
    if not token:
        logger.debug("Запрос статуса токена без параметра token")
        return JsonResponse({"status": "error", "message": "Нет токена"})

    telegram_token = TelegramToken.objects.filter(token=token).first()
    if not telegram_token:
        logger.info("Токен не найден: token=%s", token)
        return JsonResponse({"status": "invalid", "message": "Токен не найден"})

    if telegram_token.status == "used":
        logger.info("Токен уже использован: token=%s", token)
        return JsonResponse({"status": "used", "message": "Токен уже использован"})

    if telegram_token.is_expired():
        telegram_token.mark_expired()
        logger.info("Токен истек: token=%s", token)
        return JsonResponse({"status": "expired", "message": "Токен истек"})

    if telegram_token.status == "processed":
        # токен обработан ботом
        logger.info("Токен обработан ботом: token=%s", token)
        return JsonResponse({"status": "ok"})
    elif telegram_token.status == "pending":
        # токен ещё ждёт обработки
        logger.debug("Токен ожидает обработки: token=%s", token)
        return JsonResponse({"status": "pending"})
    else:
        # неизвестный или уже использованный токен
        logger.warning(
            (
                "Статус токена не позволяет авторизовать пользователя: "
                "token=%s status=%s"
            ),
            token,
            telegram_token.status,
        )
        return JsonResponse(
            {
                "status": "error",
                "message": f"Неверный статус токена: {telegram_token.status}",
            }
        )
