from django.urls import path

from ..views import invite_menu


urlpatterns = [
    path(
        "",
        invite_menu,
        name="invite_menu",
    ),
]
