import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)

from django.http import JsonResponse
from django.shortcuts import render, redirect
from yookassa import Configuration

from bot.tgbot.databases.pay_db import (
    getBannedUserId,
    getUserPay,
    createPayment,
    get_user_by_user_id,
)
from bot.tgbot.handlers.payment_irbis import (
    genPaymentYookassa_Irbis,
    checkPaymentYookassa,
)


# НАСТРОЙКИ YOOKASSA
Configuration.configure("1108748", "live_7-DWXPLohPIAHRznDkb4AysalOQLuiGfHLi_WwSbx98")


def _extract_user_id(request_user: str) -> int | None:
    parts = request_user.split("_")
    if len(parts) > 1 and parts[1].isdigit():
        return int(parts[1])
    digits_only = "".join(filter(str.isdigit, request_user))
    return int(digits_only) if digits_only else None


def irbis_menu(request):
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    telegram_id = _extract_user_id(request_user)
    if telegram_id is None:
        return redirect("telegram_login_redirect")

    user = get_user_by_user_id(telegram_id)
    step = request.GET.get("step", "init")

    # Проверка на бан
    banned = getBannedUserId(telegram_id)
    if banned != 0:
        context = {
            "user": user,
            "username": user.get("fullname") or user.get("fullName") or "Пользователь",
            "user_id": int(user.get("user_id") or telegram_id),
            "title": "DomosClub",
            "error": "⭕ Доступ запрещен",
        }
        return render(request, "main_interface/irbis/irbis.html", context)

    # Проверка подписки
    payed = getUserPay(telegram_id)
    if payed != 1:
        context = {
            "user": user,
            "username": user.get("fullname") or user.get("fullName") or "Пользователь",
            "user_id": int(user.get("user_id") or telegram_id),
            "title": "DomosClub",
            "error": "⭕ Сначала оплатите подписку!",
        }
        return render(request, "main_interface/irbis/irbis.html", context)

    # Шаг инициализации - создание платежа
    if step == "init":
        payment_id, payment_link = genPaymentYookassa_Irbis("200.00", "Проверка Irbis")
        createPayment(payment_id, 200, telegram_id)

        context = {
            "user": user,
            "username": user.get("fullname") or user.get("fullName") or "Пользователь",
            "user_id": int(user.get("user_id") or telegram_id),
            "title": "DomosClub",
            "step": "payment",
            "payment_id": payment_id,
            "payment_link": payment_link,
        }
        return render(request, "main_interface/irbis/irbis.html", context)

    # Шаг оплаты
    elif step == "payment":
        payment_id = request.GET.get("payment_id")
        payment_link = request.GET.get("payment_link")

        context = {
            "user": user,
            "username": user.get("fullname") or user.get("fullName") or "Пользователь",
            "user_id": int(user.get("user_id") or telegram_id),
            "title": "DomosClub",
            "step": "payment",
            "payment_id": payment_id,
            "payment_link": payment_link,
        }
        return render(request, "main_interface/irbis/irbis.html", context)

    # Шаг проверки оплаты
    elif step == "check_payment":
        payment_id = request.GET.get("payment_id")
        payment_link = request.GET.get("payment_link")

        context = {
            "user": user,
            "username": user.get("fullname") or user.get("fullName") or "Пользователь",
            "user_id": int(user.get("user_id") or telegram_id),
            "title": "DomosClub",
            "step": "check_payment",
            "payment_id": payment_id,
            "payment_link": payment_link,
        }
        return render(request, "main_interface/irbis/irbis.html", context)

    # Шаг выбора типа проверки (после успешной оплаты)
    elif step == "select_type":
        context = {
            "user": user,
            "username": user.get("fullname") or user.get("fullName") or "Пользователь",
            "user_id": int(user.get("user_id") or telegram_id),
            "title": "DomosClub",
            "step": "select_type",
        }
        return render(request, "main_interface/irbis/irbis.html", context)

    # Шаг заполнения формы для юр. лица
    elif step == "check_jur":
        context = {
            "user": user,
            "username": user.get("fullname") or user.get("fullName") or "Пользователь",
            "user_id": int(user.get("user_id") or telegram_id),
            "title": "DomosClub",
            "step": "check_jur",
            "form_url": (f"https://neurochief.pro/org_check?user_id={telegram_id}"),
        }
        return render(request, "main_interface/irbis/irbis.html", context)

    # Шаг заполнения формы для физ. лица
    elif step == "check_fiz":
        context = {
            "user": user,
            "username": user.get("fullname") or user.get("fullName") or "Пользователь",
            "user_id": int(user.get("user_id") or telegram_id),
            "title": "DomosClub",
            "step": "check_fiz",
            "form_url": (f"https://neurochief.pro/people_check?user_id={telegram_id}"),
        }
        return render(request, "main_interface/irbis/irbis.html", context)

    # Шаг заполнения формы для недвижимости
    elif step == "check_realty":
        context = {
            "user": user,
            "username": user.get("fullname") or user.get("fullName") or "Пользователь",
            "user_id": int(user.get("user_id") or telegram_id),
            "title": "DomosClub",
            "step": "check_realty",
            "form_url": (f"https://neurochief.pro/house_check?user_id={telegram_id}"),
        }
        return render(request, "main_interface/irbis/irbis.html", context)

    # По умолчанию - инициализация
    else:
        payment_id, payment_link = genPaymentYookassa_Irbis("200.00", "Проверка Irbis")
        createPayment(payment_id, 200, telegram_id)

        context = {
            "user": user,
            "username": user.get("fullname") or user.get("fullName") or "Пользователь",
            "user_id": int(user.get("user_id") or telegram_id),
            "title": "DomosClub",
            "step": "payment",
            "payment_id": payment_id,
            "payment_link": payment_link,
        }
        return render(request, "main_interface/irbis/irbis.html", context)


def irbis_payment_check(request, payment_id):
    """Проверка статуса оплаты для AJAX запросов"""
    status = checkPaymentYookassa(payment_id)

    # Преобразуем статус YooKassa в числовой формат (как в payment_sub_check)
    if status == "succeeded":
        return JsonResponse({"status": 1})
    elif status == "pending":
        return JsonResponse({"status": 0})
    else:
        return JsonResponse({"status": -1})
