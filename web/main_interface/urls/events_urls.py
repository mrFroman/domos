from django.urls import path

from ..views import events_menu, event_detail


urlpatterns = [
    path(
        "",
        events_menu,
        name="events_menu",
    ),
    path(
        "<str:event_id>/",
        event_detail,
        name="event_detail",
    ),
]
