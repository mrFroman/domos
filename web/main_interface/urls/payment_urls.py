from django.urls import path

from web.main_interface.views import payment_menu, payment_sub_check


urlpatterns = [
    path(
        "",
        payment_menu,
        name="payment_menu",
    ),
    path(
        "payment_sub_check/<int:payment_id>/",
        payment_sub_check,
        name="payment_sub_check",
    ),
]
