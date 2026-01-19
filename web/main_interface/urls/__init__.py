from django.urls import path, include

from ..views import main_menu, assistant_view, services_view, subscriptions_view, my_requests_view, admin_dashboard_view

urlpatterns = [
    path("", main_menu, name="main_menu"),
    path("assistant/", assistant_view, name="assistant"),
    path("services/", services_view, name="services"),
    path("subscriptions/", subscriptions_view, name="subscriptions"),
    path("my-requests/", my_requests_view, name="my_requests"),
    path("admin-dashboard/", admin_dashboard_view, name="admin_dashboard"),
    path("auth/", include("web.main_interface.urls.auth_urls")),
    path("advert/", include("web.main_interface.urls.advert_urls")),
    path("contract/", include("web.main_interface.urls.contract_urls")),
    path("events/", include("web.main_interface.urls.events_urls")),
    path("admin-panel/", include("web.main_interface.urls.admin_urls")),
    path("helpful/", include("web.main_interface.urls.helpful_urls")),
    path("invite/", include("web.main_interface.urls.invite_urls")),
    path("meeting/", include("web.main_interface.urls.meeting_urls")),
    path("payments/", include("web.main_interface.urls.payment_urls")),
    path("rules/", include("web.main_interface.urls.rules_urls")),
    path("lawyer/", include("web.main_interface.urls.lawyer_urls")),
    path("irbis/", include("web.main_interface.urls.irbis_urls")),
]
