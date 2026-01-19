from django.urls import path

from web.main_interface.views import advert_menu


urlpatterns = [
    path(
        "",
        advert_menu,
        name="advert_menu",
    ),
]
