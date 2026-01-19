from django.urls import path

from ..views import (
    admin_add_contact,
    admin_add_realtor,
    admin_advert_management,
    admin_advert_queries,
    admin_advert_requests,
    admin_analytics,
    admin_broadcast,
    admin_feedback_table,
    admin_find_user,
    admin_legal_requests,
    admin_paid,
    admin_unpaid,
)

urlpatterns = [
    path("analytics/", admin_analytics, name="admin_analytics"),
    path("broadcast/", admin_broadcast, name="admin_broadcast"),
    path("find-user/", admin_find_user, name="admin_find_user"),
    path("unpaid/", admin_unpaid, name="admin_unpaid"),
    path("paid/", admin_paid, name="admin_paid"),
    path("legal-requests/", admin_legal_requests, name="admin_legal_requests"),
    path(
        "advert-requests/",
        admin_advert_requests,
        name="admin_advert_requests",
    ),
    path(
        "advert-queries/",
        admin_advert_queries,
        name="admin_advert_queries",
    ),
    path(
        "advert-management/",
        admin_advert_management,
        name="admin_advert_management",
    ),
    path(
        "feedback-table/",
        admin_feedback_table,
        name="admin_feedback_table",
    ),
    path("add-realtor/", admin_add_realtor, name="admin_add_realtor"),
    path("add-contact/", admin_add_contact, name="admin_add_contact"),
]
