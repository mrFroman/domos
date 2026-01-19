from django.urls import path
from web.main_interface.views import lawyer_menu, upload_lawyer_file

urlpatterns = [
    path("", lawyer_menu, name="lawyer_menu"),
    path("upload_file/", upload_lawyer_file, name="upload_lawyer_file"),
]