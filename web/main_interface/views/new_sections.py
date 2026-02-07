import sys
import os
import asyncio
import json

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from bot.tgbot.databases.pay_db import get_user_by_user_id, getUserPay, getBannedUserId, changeUserAdmin


def _extract_user_id(request_user: str) -> int | None:
    """Извлечь telegram_id из строки пользователя"""
    parts = request_user.split("_")
    if len(parts) > 1 and parts[1].isdigit():
        return int(parts[1])
    digits_only = "".join(filter(str.isdigit, request_user))
    return int(digits_only) if digits_only else None


def _is_admin(user_id: int | None) -> bool:
    """Проверить, является ли пользователь администратором"""
    if not user_id:
        return False
    
    from bot.tgbot.databases.pay_db import changeUserAdmin
    
    result = None
    try:
        result = changeUserAdmin(user_id)
        return result == "usered"
    finally:
        if result in {"admined", "usered"}:
            changeUserAdmin(user_id)


def assistant_view(request):
    """Раздел Помощник - заглушка для будущего AI-бота"""
    from bot.tgbot.databases.pay_db import get_user_by_user_id
    
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    telegram_id = _extract_user_id(request_user)
    if telegram_id is None:
        return redirect("telegram_login_redirect")

    user = get_user_by_user_id(telegram_id)

    context = {
        "user": user,
        "username": user.get("fullname") or user.get("fullName") or "Пользователь",
        "user_id": int(user.get("user_id") or telegram_id),
        "title": "Помощник - DomosClub",
        "page_title": "Ваш персональный помощник Domos",
        "page_subtitle": "Задайте вопрос или выберите действие",
        "is_admin": _is_admin(telegram_id),
    }
    return render(request, "main_interface/assistant.html", context)


@require_POST
@csrf_exempt
def assistant_chat_api(request):
    """
    API для чата с AI-помощником (та же логика, что в боте).
    POST JSON: {"message": "текст запроса"} -> {"answer": "ответ ИИ"} или {"error": "..."}
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Необходима авторизация"}, status=401)

    request_user = str(request.user)
    telegram_id = _extract_user_id(request_user)
    if telegram_id is None:
        return JsonResponse({"error": "Пользователь не найден"}, status=401)

    if getBannedUserId(telegram_id) != 0:
        return JsonResponse({"error": "Ваш аккаунт заблокирован."}, status=403)

    if getUserPay(telegram_id) != 1:
        return JsonResponse({"error": "Сначала оплатите подписку!"}, status=403)

    try:
        body = json.loads(request.body or "{}")
        message = (body.get("message") or "").strip()
    except json.JSONDecodeError:
        return JsonResponse({"error": "Неверный формат запроса"}, status=400)

    if not message:
        return JsonResponse({"error": "Сообщение не может быть пустым"}, status=400)

    try:
        from bot.tgbot.handlers.yandex_gpt_handler import run_chat_with_tools
        answer = asyncio.run(run_chat_with_tools(user_id=telegram_id, user_msg=message))
    except Exception as e:
        return JsonResponse({"error": f"Ошибка при обработке запроса: {e}"}, status=500)

    return JsonResponse({"answer": answer or "Извините, не удалось получить ответ."})


def services_view(request):
    """Раздел Сервисы - карточки всех доступных сервисов"""
    from bot.tgbot.databases.pay_db import get_user_by_user_id, getUserPay
    
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    telegram_id = _extract_user_id(request_user)
    if telegram_id is None:
        return redirect("telegram_login_redirect")

    user = get_user_by_user_id(telegram_id)
    payed = getUserPay(telegram_id)

    # Определяем статус подписки для каждого сервиса
    services = [
        {
            "name": "Сформировать договор",
            "icon": "📝",
            "description": "Создание договоров различных типов",
            "url": "create_contract_menu",
            "available": True,
            "requires_subscription": False,
        },
        {
            "name": "Заявка юристу",
            "icon": "📠",
            "description": "Получить консультацию юриста",
            "url": "lawyer_menu",
            "available": payed == 1,
            "requires_subscription": True,
        },
        {
            "name": "Проверка IRBIS",
            "icon": "🔍",
            "description": "Проверка объектов в базе IRBIS",
            "url": "irbis_menu",
            "available": payed == 1,
            "requires_subscription": True,
        },
        {
            "name": "Заявка на рекламу",
            "icon": "📮",
            "description": "Подать заявку на размещение рекламы",
            "url": "advert_menu",
            "available": True,
            "requires_subscription": False,
        },
        {
            "name": "Переговорка",
            "icon": "💬",
            "description": "Забронировать переговорную комнату",
            "url": "meeting_booking",
            "available": True,
            "requires_subscription": False,
        },
    ]

    context = {
        "user": user,
        "username": user.get("fullname") or user.get("fullName") or "Пользователь",
        "user_id": int(user.get("user_id") or telegram_id),
        "title": "Сервисы - DomosClub",
        "page_title": "Сервисы",
        "page_subtitle": "Все доступные инструменты в одном месте",
        "services": services,
        "is_admin": _is_admin(telegram_id),
    }
    return render(request, "main_interface/services.html", context)


def subscriptions_view(request):
    """Раздел Подписки и оплаты"""
    from bot.tgbot.databases.pay_db import get_user_by_user_id
    
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    telegram_id = _extract_user_id(request_user)
    if telegram_id is None:
        return redirect("telegram_login_redirect")

    user = get_user_by_user_id(telegram_id)
    pay_status = user.get("pay_status", 0)
    end_pay = user.get("end_pay", None)

    context = {
        "user": user,
        "username": user.get("fullname") or user.get("fullName") or "Пользователь",
        "user_id": int(user.get("user_id") or telegram_id),
        "title": "Подписки и оплаты - DomosClub",
        "page_title": "Подписки и оплаты",
        "page_subtitle": "Управление подпиской и история платежей",
        "pay_status": pay_status,
        "end_pay": end_pay,
        "is_admin": _is_admin(telegram_id),
    }
    return render(request, "main_interface/subscriptions.html", context)


def my_requests_view(request):
    """Раздел Мои заявки - заглушка"""
    from bot.tgbot.databases.pay_db import get_user_by_user_id
    
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    telegram_id = _extract_user_id(request_user)
    if telegram_id is None:
        return redirect("telegram_login_redirect")

    user = get_user_by_user_id(telegram_id)

    # Заглушка - в будущем здесь будут реальные заявки
    requests = []

    context = {
        "user": user,
        "username": user.get("fullname") or user.get("fullName") or "Пользователь",
        "user_id": int(user.get("user_id") or telegram_id),
        "title": "Мои заявки - DomosClub",
        "page_title": "Мои заявки",
        "page_subtitle": "История всех ваших заявок",
        "requests": requests,
        "is_admin": _is_admin(telegram_id),
    }
    return render(request, "main_interface/my_requests.html", context)


def admin_dashboard_view(request):
    """Главная страница админ-панели"""
    from bot.tgbot.databases.pay_db import get_user_by_user_id
    
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    telegram_id = _extract_user_id(request_user)
    if telegram_id is None:
        return redirect("telegram_login_redirect")

    if not _is_admin(telegram_id):
        return redirect("main_menu")

    user = get_user_by_user_id(telegram_id)

    context = {
        "user": user,
        "username": user.get("fullname") or user.get("fullName") or "Пользователь",
        "user_id": int(user.get("user_id") or telegram_id),
        "title": "Админ-панель - DomosClub",
        "page_title": "Панель администратора",
        "page_subtitle": "Управление платформой",
        "is_admin": True,
    }
    return render(request, "main_interface/admin/dashboard.html", context)
