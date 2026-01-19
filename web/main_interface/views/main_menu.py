import sys
import os

from django.shortcuts import render, redirect
from bot.tgbot.databases.pay_db import changeUserAdmin

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)

from bot.tgbot.databases.pay_db import get_user_by_user_id


def _extract_user_id(request_user: str) -> int | None:
    parts = request_user.split("_")
    if len(parts) > 1 and parts[1].isdigit():
        return int(parts[1])
    digits_only = "".join(filter(str.isdigit, request_user))
    return int(digits_only) if digits_only else None


def _is_admin(user_id: int | None) -> bool:
    if not user_id:
        return False

    result = None
    try:
        result = changeUserAdmin(user_id)
        return result == "usered"
    finally:
        if result in {"admined", "usered"}:
            changeUserAdmin(user_id)


def main_menu(request):
    if not request.user.is_authenticated:
        print(request.user.is_authenticated)
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
        "username": user["fullName"],
        "user_id": int(user["user_id"]),
        "title": "DomosClub",
        "page_title": "Вы в главном меню DomosClub",
        "is_admin": _is_admin(telegram_id),
    }
    return render(request, "main_interface/main_menu.html", context)
