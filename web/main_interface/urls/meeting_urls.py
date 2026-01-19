from django.urls import path

from web.main_interface.views import meeting_booking


urlpatterns = [
    path(
        "booking/",
        meeting_booking,
        name="meeting_booking",
    ),
]
