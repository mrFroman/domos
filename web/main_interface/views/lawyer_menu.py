import os
import pytz
import requests
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect

from bot.tgbot.databases.pay_db import (
    getBannedUserId,
    getUserPay,
    get_user_info,
    save_request_to_db,
)
from bot.tgbot.services.email_message_sender import send_email

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


HOST_TURN = os.getenv("HOST_TURN", "False").strip().lower() == "true"
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Установка часового пояса Екатеринбурга
YEKATERINBURG_TZ = pytz.timezone("Asia/Yekaterinburg")

if HOST_TURN:
    LAWYER_IDS = [
        i.strip() for i in os.getenv("LAWYER_IDS", "").split(",") if i.strip()
    ]
else:
    LAWYER_IDS = [
        i.strip() for i in os.getenv("TEST_LAWYER_IDS", "").split(",") if i.strip()
    ]

MEDIA_ROOT = getattr(settings, "MEDIA_ROOT", "media")


def _extract_user_id(request_user: str) -> int | None:
    parts = request_user.split("_")
    if len(parts) > 1 and parts[1].isdigit():
        return int(parts[1])
    digits_only = "".join(filter(str.isdigit, request_user))
    return int(digits_only) if digits_only else None


def _send_telegram_message(chat_id, text):
    """Отправка текстового сообщения через Telegram Bot API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data)
        return response.status_code == 200
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
        return False


def _send_telegram_document(chat_id, document_path):
    """Отправка документа через Telegram Bot API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        with open(document_path, "rb") as doc:
            files = {"document": doc}
            data = {"chat_id": chat_id}
            response = requests.post(url, data=data, files=files)
            return response.status_code == 200
    except Exception as e:
        print(f"Ошибка отправки документа: {e}")
        return False


def _send_telegram_voice(chat_id, voice_path):
    """Отправка голосового сообщения через Telegram Bot API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice"
    try:
        with open(voice_path, "rb") as voice:
            files = {"voice": voice}
            data = {
                "chat_id": chat_id,
                "caption": "Голосовое сообщение от пользователя",
            }
            response = requests.post(url, data=data, files=files)
            return response.status_code == 200
    except Exception as e:
        print(f"Ошибка отправки голосового сообщения: {e}")
        return False


def lawyer_menu(request):
    # Проверка аутентификации
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    telegram_id = _extract_user_id(request_user)
    if telegram_id is None:
        return redirect("telegram_login_redirect")

    session = request.session
    step = request.POST.get(
        "step", request.GET.get("step", session.get("step", "awaiting_question"))
    )

    # Проверка на бан
    banned = getBannedUserId(telegram_id)
    if banned != 0:
        context = {
            "title": "DomosClub",
            "page_title": "Заявка юристу",
            "description": "⭕ Доступ запрещен",
            "step": "error",
            "error": None,
        }
        return render(request, "main_interface/lawyer/lawyer.html", context)

    # Проверка подписки
    payed = getUserPay(telegram_id)
    if payed != 1:
        context = {
            "title": "DomosClub",
            "page_title": "Заявка юристу",
            "description": "⭕ Сначала оплатите подписку!",
            "step": "error",
            "error": None,
        }
        return render(request, "main_interface/lawyer/lawyer.html", context)

    # Получаем информацию о пользователе
    user_info = get_user_info(telegram_id)
    username = user_info.get("fullName") or str(request.user)

    files = [os.path.basename(f) for f in session.get("files", [])]
    context = {
        "title": "DomosClub",
        "page_title": "Заявка юристу",
        "description": "",
        "step": step,
        "error": None,
        "files": files,
        "processed_text": session.get("processed_text", ""),
        "user_id": telegram_id,
    }

    # Шаг 1: Ожидание вопроса
    if step == "awaiting_question":
        context["description"] = (
            "Опишите какой документ вам нужен, опишите все детали, "
            "стороны, предмет, суммы и прочее.\n\n"
            "Вы можете отправить ваш вопрос голосовым сообщением или текстом"
        )
        session["step"] = "awaiting_question"
        session.modified = True

    # Обработка POST запросов
    elif request.method == "POST":
        # Обработка текстового вопроса
        if step == "awaiting_question" and "text_question" in request.POST:
            session["request_type"] = "text"
            session["original_text"] = request.POST["text_question"]
            session["processed_text"] = request.POST["text_question"]
            session["step"] = "adding_documents"
            session.modified = True
            context["step"] = "adding_documents"
            context["description"] = "Вы можете прикрепить до 5 файлов."
            context["processed_text"] = request.POST["text_question"]

        # Обработка голосового файла
        elif step == "awaiting_question" and "voice_file" in request.FILES:
            session["request_type"] = "voice"
            voice_file = request.FILES["voice_file"]

            # Сохраняем голосовой файл
            current_date = datetime.now().strftime("%d.%m.%Y-%H.%M")
            base_dir = os.path.join(
                MEDIA_ROOT, "lawyer_docs", f"{telegram_id}_{current_date}"
            )
            os.makedirs(base_dir, exist_ok=True)

            voice_path = os.path.join(base_dir, voice_file.name)
            with open(voice_path, "wb") as dest:
                for chunk in voice_file.chunks():
                    dest.write(chunk)

            session["voice_file_path"] = voice_path

            # Обрабатываем голос через Yandex SpeechKit
            try:
                # Для обработки голоса нужен file_id от Telegram бота
                # В веб-версии мы можем использовать прямой путь к файлу
                # или сохранить file_id если есть интеграция с ботом
                processed_text = "Голосовое сообщение получено. Обработка текста..."
                # TODO: Реализовать обработку голоса через Yandex SpeechKit
                # processed_text = await process_voice_with_yandex(...)
                session["processed_text"] = processed_text
            except Exception as e:
                context["error"] = f"Ошибка обработки голоса: {e}"
                session["processed_text"] = "Голосовое сообщение получено"

            session["step"] = "adding_documents"
            session.modified = True
            context["step"] = "adding_documents"
            context["description"] = "Вы можете прикрепить до 5 файлов."
            context["processed_text"] = session["processed_text"]

        # Переход к выбору срочности
        elif step == "adding_documents" and "next_to_urgency" in request.POST:
            session["step"] = "choosing_urgency"
            session.modified = True
            context["step"] = "choosing_urgency"
            context["description"] = "Выберите срочность обработки вашего запроса:"

        # Обработка срочности и отправка
        elif step == "choosing_urgency" and "urgency" in request.POST:
            urgency = request.POST["urgency"]
            session["urgency"] = urgency
            processed_text = session.get("processed_text", "")
            files = session.get("files", [])

            # Формируем сообщение для юриста
            sender_name = (
                user_info.get("full_name")
                or user_info.get("fullName")
                or f"Пользователь с ID {telegram_id}"
            )
            user_link = f"@{username}"

            urgency_text_map = {
                "urgent": "🔴 СРОЧНО (1 день)",
                "normal": "🟡 Обычный (2 дня)",
                "complex": "⚫ Сложный (3 дня)",
            }
            urgency_text = urgency_text_map.get(urgency, "Не указано")

            message_text = (
                f"📨 Вам поступил новый запрос\n\n"
                f"👤 От: {sender_name}\n"
                f"📞 Связаться: {user_link}\n"
                f"⏱ Срочность: {urgency_text}\n\n"
                f"📝 Текст запроса:\n{processed_text}"
            )

            # Сохраняем в БД
            now = datetime.now(YEKATERINBURG_TZ)
            try:
                save_request_to_db(
                    "lawyer", now, processed_text, sender_name, user_link
                )
            except Exception as e:
                print(f"Ошибка сохранения в БД: {e}")

            # Отправка email
            is_email_success = False
            try:
                send_email(
                    msg_subj=f"Заявка на юридическую помощь от {sender_name}",
                    msg_text=message_text,
                    files=files,
                )
                is_email_success = True
            except Exception as e:
                print(f"Ошибка отправки сообщения на почту: {e}")
                context["error"] = f"Ошибка отправки email: {e}"

            # Отправка Telegram сообщений юристам
            is_telegram_success = False
            try:
                for lawyer_id in LAWYER_IDS:
                    # Отправляем текстовое сообщение
                    _send_telegram_message(lawyer_id, message_text)

                    # Отправляем документы
                    for file_path in files:
                        if os.path.exists(file_path):
                            _send_telegram_document(lawyer_id, file_path)

                    # Отправляем голосовое сообщение, если есть
                    voice_file_path = session.get("voice_file_path")
                    if voice_file_path and os.path.exists(voice_file_path):
                        _send_telegram_voice(lawyer_id, voice_file_path)

                is_telegram_success = True
            except Exception as e:
                print(f"Ошибка при отправке сообщения юристу: {e}")
                context["error"] = f"Ошибка отправки в Telegram: {e}"

            # Формируем сообщение об успехе
            if is_email_success and is_telegram_success:
                context["description"] = "✅ Ваш запрос отправлен юристу. Спасибо!"
            elif is_email_success:
                context["description"] = (
                    "✅ Ваш запрос отправлен юристу на электронную почту. " "Спасибо!"
                )
            elif is_telegram_success:
                context["description"] = (
                    "✅ Ваш запрос отправлен юристу в Telegram. Спасибо!"
                )
            else:
                context["description"] = "❌ Ошибка при отправке"

            session.clear()  # Сброс сессии после завершения
            context["step"] = "finished"

    return render(request, "main_interface/lawyer/lawyer.html", context)


def upload_lawyer_file(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    request_user = str(request.user)
    telegram_id = _extract_user_id(request_user)
    if telegram_id is None:
        return JsonResponse({"error": "Invalid user"}, status=401)

    # Создаем директорию для файлов пользователя
    current_date = datetime.now().strftime("%d.%m.%Y-%H.%M")
    user_dir = os.path.join(MEDIA_ROOT, "lawyer_docs", f"{telegram_id}_{current_date}")
    os.makedirs(user_dir, exist_ok=True)

    uploaded_files = request.FILES.getlist("files")
    if "files" not in request.session:
        request.session["files"] = []

    response_files = []

    for f in uploaded_files:
        if len(request.session["files"]) >= 5:
            break
        file_path = os.path.join(user_dir, f.name)
        with open(file_path, "wb") as dest:
            for chunk in f.chunks():
                dest.write(chunk)

        request.session["files"].append(file_path)
        response_files.append(f.name)

    request.session.modified = True
    return JsonResponse(
        {"uploaded": response_files, "count": len(request.session["files"])}
    )
