from django.urls import path

from ..views import helpful_menu


urlpatterns = [
    path(
        "",
        helpful_menu,
        name="helpful_menu",
    ),
]
