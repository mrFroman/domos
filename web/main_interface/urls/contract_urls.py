from django.urls import path

from web.main_interface.views import (
    check_processing_status,
    confirm_contract,
    create_contract_menu,
    download_files,
    download_offer,
    start_passport_flow,
    upload_passport_page,
    upload_passport_photo,
    upload_registration_photo,
)
from ..views.contract_menu import download_contract


urlpatterns = [
    path(
        "create_contract_menu/",
        create_contract_menu,
        name="create_contract_menu",
    ),
    path(
        "confirm_contract/",
        confirm_contract,
        name="confirm_contract",
    ),
    path(
        "upload_passport/<str:passport_type>/",
        upload_passport_page,
        name="upload_passport_page",
    ),
    path(
        "upload_passport_photo/",
        upload_passport_photo,
        name="upload_passport_photo",
    ),
    path(
        "upload_registration_photo/",
        upload_registration_photo,
        name="upload_registration_photo",
    ),
    path(
        "start_passport_flow/",
        start_passport_flow,
        name="start_passport_flow",
    ),
    path(
        "check_processing_status/",
        check_processing_status,
        name="check_processing_status",
    ),
    path(
        "download_contract/<str:token>/",
        download_contract,
        name="download_contract",
    ),
    path(
        "download/<str:doc_type>/",
        download_files,
        name="download_files",
    ),
    path(
        "download-offer/",
        download_offer,
        name="download_offer",
    ),
]
