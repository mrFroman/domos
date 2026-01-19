from django.urls import path

from web.main_interface.views import irbis_menu, irbis_payment_check


urlpatterns = [
    path(
        "",
        irbis_menu,
        name="irbis_menu",
    ),
    path(
        "payment_check/<str:payment_id>",
        irbis_payment_check,
        name="irbis_payment_check",
    ),
]
