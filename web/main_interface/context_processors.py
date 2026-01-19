import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)

from bot.tgbot.databases.pay_db import get_user_by_user_id
from .views.main_menu import _extract_user_id, _is_admin


def user_context(request):
    """Context processor для передачи информации о пользователе во все шаблоны"""
    context = {
        "username": None,
        "is_admin": False,
    }

    if request.user.is_authenticated:
        request_user = str(request.user)
        if request_user:
            telegram_id = _extract_user_id(request_user)
            if telegram_id is not None:
                try:
                    user = get_user_by_user_id(telegram_id)
                    context["username"] = user.get("fullName", "Пользователь")
                    context["is_admin"] = _is_admin(telegram_id)
                except Exception:
                    pass

    return context
