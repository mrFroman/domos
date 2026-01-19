import os
import zipfile
from io import BytesIO

from django.http import FileResponse, HttpResponseNotFound
from django.shortcuts import render, redirect

from config import BASE_DIR


FORMS = {
    "helpfulblank1": [
        os.path.join(BASE_DIR, "bot", "blanks", "Авансовое соглашение(бланк-ФЛ).docx"),
        os.path.join(BASE_DIR, "bot", "blanks", "Авансовое соглашение(бланк-ИП).docx"),
    ],
    "helpfulblank2": [
        os.path.join(BASE_DIR, "bot", "blanks", "Договор аренды(бланк).docx")
    ],
    "helpfulblank3": [
        os.path.join(BASE_DIR, "bot", "blanks", "Ипотека(бланк-ФЛ).docx"),
        os.path.join(BASE_DIR, "bot", "blanks", "Ипотека(бланк-ИП).docx"),
        os.path.join(BASE_DIR, "bot", "blanks", "Ипотека(бланк-Самозанятый).docx"),
    ],
    "helpfulblank4": [
        os.path.join(BASE_DIR, "bot", "blanks", "Обмен(бланк-ФЛ).docx"),
        os.path.join(BASE_DIR, "bot", "blanks", "Обмен(бланк-ИП).docx"),
        os.path.join(BASE_DIR, "bot", "blanks", "Обмен(бланк-Самозанятый).docx"),
    ],
    "helpfulblank5": [
        os.path.join(BASE_DIR, "bot", "blanks", "ПДКП_без поручительства(бланк).docx"),
    ],
    "helpfulblank6": [
        os.path.join(BASE_DIR, "bot", "blanks", "Подбор(бланк-ФЛ).docx"),
        os.path.join(BASE_DIR, "bot", "blanks", "Подбор(бланк-ИП).docx"),
        os.path.join(BASE_DIR, "bot", "blanks", "Подбор(бланк-Самозанятый).docx"),
    ],
    "helpfulblank7": [
        os.path.join(BASE_DIR, "bot", "blanks", "Продажа(бланк-ФЛ).docx"),
        os.path.join(BASE_DIR, "bot", "blanks", "Продажа(бланк-ИП).docx"),
        os.path.join(BASE_DIR, "bot", "blanks", "Продажа(бланк-Самозанятый).docx"),
    ],
    "helpfulblank8": [
        os.path.join(
            BASE_DIR, "bot", "blanks", "Расторжение договора услуг(бланк).doc"
        ),
    ],
    "helpfulblank9": [
        os.path.join(
            BASE_DIR, "bot", "blanks", "Юридическое сопровождение(бланк-ФЛ).docx"
        ),
        os.path.join(
            BASE_DIR, "bot", "blanks", "Юридическое сопровождение(бланк-ИП).docx"
        ),
        os.path.join(
            BASE_DIR,
            "bot",
            "blanks",
            "Юридическое сопровождение(бланк-Самозанятый).docx",
        ),
    ],
    "helpfulblank10": [
        os.path.join(
            BASE_DIR, "bot", "blanks", "Соглашение о расторжении аванса(бланк).docx"
        ),
    ],
    "helpfulblank11": [
        os.path.join(
            BASE_DIR,
            "bot",
            "blanks",
            "Уведомление завышения-занижения краткое(бланк).docx",
        ),
    ],
    "helpfulblank12": [
        os.path.join(
            BASE_DIR,
            "bot",
            "blanks",
            "Уведомление завышения-занижения полное(бланк).docx",
        ),
    ],
    "helpfulblank13": [
        os.path.join(
            BASE_DIR, "bot", "blanks", "Уведомление о перепланировке(бланк).doc"
        ),
    ],
    "helpfulblank14": [
        os.path.join(BASE_DIR, "bot", "blanks", "Акт выполненных работ(бланк).doc"),
    ],
}


def helpful_menu(request):
    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    step = request.GET.get("step", "main")
    context = {
        "step": step,
        "title": "DomosClub",
        "page_title": "Полезное",
    }
    return render(request, "main_interface/helpful/helpful.html", context)


def download_files(request, doc_type):
    """
    Возвращает zip-архив с файлами по типу документа.
    Пример: /download/avans/ или /download/ipoketa/
    """
    files = FORMS.get(doc_type)
    if not files:
        return HttpResponseNotFound("Неизвестный тип документа.")

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        for file_path in files:
            if os.path.exists(file_path):
                zip_file.write(file_path, os.path.basename(file_path))
    buffer.seek(0)

    response = FileResponse(buffer, as_attachment=True, filename=f"{doc_type}.zip")
    return response
