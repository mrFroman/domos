from django.urls import path

from web.main_interface.views import (
    login,
    telegram_auth_callback,
    check_telegram_token,
)


urlpatterns = [
    path(
        "login/",
        login,
        name="telegram_login_redirect",
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
