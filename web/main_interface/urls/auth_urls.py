from django.urls import path

from web.main_interface.views import (
    login,
    telegram_auth_callback,
    check_telegram_token,
)
from web.main_interface.views.phone_auth import (
    phone_login,
    phone_enter_telegram_id,
    phone_verify_code,
    resend_code,
)


urlpatterns = [
    # Основная авторизация через Telegram токен
    path(
        "login/",
        login,
        name="telegram_login_redirect",
    ),
    # Авторизация по номеру телефона (альтернативный способ)
    path(
        "phone-login/",
        phone_login,
        name="phone_login",
    ),
    path(
        "enter-telegram-id/",
        phone_enter_telegram_id,
        name="phone_enter_telegram_id",
    ),
    path(
        "verify-code/",
        phone_verify_code,
        name="phone_verify_code",
    ),
    path(
        "resend-code/",
        resend_code,
        name="resend_code",
    ),
    path(
        "telegram/",
        telegram_auth_callback,
        name="telegram_auth_callback",
    ),
    path(
        "check_token/",
        check_telegram_token,
        name="check_telegram_token",
    ),
]
