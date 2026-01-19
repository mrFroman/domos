from django.urls import path

from web.main_interface.views import rules_menu


urlpatterns = [
    path(
        "",
        rules_menu,
        name="rules_menu",
    ),
]
