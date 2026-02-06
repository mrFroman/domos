import aiohttp
import threading
import os
import sys
import secrets
import asyncio
import sqlite3
import json
from asgiref.sync import sync_to_async
from datetime import datetime

from django.shortcuts import render, redirect
from django.http import JsonResponse, FileResponse, Http404
from django.urls import reverse
from typing import cast
from aiogram.dispatcher import FSMContext
from django.views.decorators.csrf import csrf_exempt

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
from bot.tgbot.databases.pay_db import (
    get_user_by_user_id,
    get_rieltor_data,
    get_last_client_data,
    format_passport_data,
    check_passport_exists,
    check_passport_client_exists,
    getBannedUserId,
    getUserPay,
    save_passport,
)
from bot.tgbot.fast_app.function import generate_contract as tg_generate_contract
from bot.tgbot.services.photo_yandex_gpt import *
from config import BASE_DIR, CONTRACT_TOKENS_DB_PATH, logger_bot


def create_contract_menu(request):
    """Главная страница создания договоров - аналог command_dogovor_handler"""
    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    telegram_id = int("".join(filter(str.isdigit, request_user)))
    user = get_user_by_user_id(telegram_id)

    banned = getBannedUserId(telegram_id)
    if banned != 0:
        context = {
            "title": "DomosClub",
            "page_title": "Доступ запрещен",
            "message": "Пользователь заблокирован!",
        }
        return render(request, "main_interface/access_denied.html", context)

    pay_status = getUserPay(telegram_id)
    if pay_status != 1:
        context = {
            "title": "DomosClub",
            "page_title": "Доступ запрещен",
            "message": "⭕ Сначала оплатите подписку!",
        }
        return render(request, "main_interface/access_denied.html", context)

    # Проверяем наличие данных паспорта
    rieltor_exists = check_passport_exists(telegram_id)
    client_exists = check_passport_client_exists(telegram_id)

    message = None
    show_upload_buttons = False
    upload_message = None

    if not rieltor_exists:
        upload_message = "❌ Не найдены данные паспорта риелтора"
        show_upload_buttons = True
    elif client_exists == 1:
        upload_message = "❌ Не найдены данные паспорта клиента"
        show_upload_buttons = True
    elif rieltor_exists and client_exists != 1:
        message = f"✅ Последний клиент: {client_exists}"

    context = {
        "title": "DomosClub",
        "page_title": "Формирование договора",
        "user": user,
        "user_id": telegram_id,
        "message": message,
        "upload_message": upload_message,
        "show_upload_buttons": show_upload_buttons,
        "rieltor_exists": rieltor_exists,
        "client_exists": client_exists,
        "last_client_name": client_exists if client_exists != 1 else None,
    }
    return render(
        request,
        "main_interface/contract/create_contract_menu.html",
        context,
    )


async def start_passport_flow(request):
    # Проверка аутентификации через sync_to_async
    user = await sync_to_async(lambda: request.user)()
    is_authenticated = await sync_to_async(lambda: user.is_authenticated)()

    if not is_authenticated:
        return redirect("telegram_login_redirect")

    # Получаем telegram_id из сессии
    user_id = await sync_to_async(lambda: request.session.get("telegram_id"))()
    if not user_id:
        return redirect("telegram_login_redirect")

    user = get_user_by_user_id(int(user_id))
    variant = request.GET.get("variant")
    doc_type = request.GET.get("doc_type")
    token = secrets.token_urlsafe(16)

    if variant == "new_client":
        return redirect("upload_passport_page", passport_type="client")

    if variant == "continue":
        if not doc_type:
            return redirect("create_contract_menu")
        payload = _build_passport_payload_for_edit_link(user_id, doc_type)
        if not payload:
            return redirect("create_contract_menu")

        # ✅ await асинхронной функции
        res = await send_passport_edit_link_web(user_id, token, payload)
        if res.get("success"):
            # Запускаем фоновую задачу в отдельном потоке с собственным event loop,
            # чтобы избежать проблем с жизненным циклом текущего цикла.
            def _runner():
                asyncio.run(wait_for_signal_and_process_web(token, user_id, payload))

            threading.Thread(target=_runner, daemon=True).start()

            context = {
                "title": "DomosClub",
                "page_title": "Редактирование данных",
                "message": "📝 Нажмите на кнопку, чтобы отредактировать данные перед генерацией договора",
                "edit_url": res["edit_url"],
                "payload": payload,
                "doc_type": payload["doc_type"],
                "token": token,  # Добавляем токен для отслеживания статуса
            }
            return render(
                request, "main_interface/contract/contract_confirmation.html", context
            )

        context = {
            "title": "DomosClub",
            "page_title": "Ошибка",
            "message": f"❌ {res.get('message', 'Не удалось сформировать ссылку')}",
        }
        return render(request, "main_interface/access_denied.html", context)

    return redirect("create_contract_menu")


def confirm_contract(request):
    """Обработка подтверждения и формирования договора - аналог process_correction"""
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    user_id = request.session.get("telegram_id")
    if not user_id:
        return redirect("telegram_login_redirect")

    user = get_user_by_user_id(int(user_id))

    if request.method != "POST":
        return redirect("create_contract_menu")

    doc_type = request.POST.get("doc_type")
    corrected_data = request.POST.get("corrected_data", "")

    if not corrected_data:
        context = {
            "title": "DomosClub",
            "page_title": "Ошибка",
            "message": "Не получены данные для обработки",
        }
        return render(request, "main_interface/access_denied.html", context)

    try:
        # Парсим JSON данные, полученные от JavaScript
        try:
            passport_data = json.loads(corrected_data)
        except json.JSONDecodeError:
            context = {
                "title": "DomosClub",
                "page_title": "Ошибка",
                "message": "❌ Неверный формат данных. Попробуйте еще раз.",
            }
            return render(request, "main_interface/access_denied.html", context)

        # Формируем данные для генерации договора
        contract_data = {"doc_type": doc_type, "passport_data": passport_data}

        # Генерируем договор
        contract_result = generate_contract(user_id, contract_data)

        if contract_result["success"]:
            context = {
                "title": "DomosClub",
                "page_title": "Договор сформирован",
                "message": f'✅ Договор успешно сформирован!<br><br>{contract_result["message"]}',
                "download_url": contract_result.get("download_url"),
            }
        else:
            context = {
                "title": "DomosClub",
                "page_title": "Ошибка формирования",
                "message": f'❌ Ошибка при формировании договора: {contract_result["message"]}',
            }

        return render(request, "main_interface/contract/contract_result.html", context)

    except Exception as e:
        context = {
            "title": "DomosClub",
            "page_title": "Ошибка",
            "message": f"❌ Произошла ошибка: {str(e)}",
        }
        return render(request, "main_interface/access_denied.html", context)


def generate_contract(user_id, contract_data):
    """Генерирует договор для веб-интерфейса - аналог send_passport_edit_link1"""
    try:
        # Здесь должна быть логика генерации договора
        # Пока что возвращаем заглушку

        doc_type_names = {
            "1": "Авансовое соглашение",
            "2": "Договор аренды",
            "3": "Ипотека",
            "4": "Обмен",
            "6": "Подбор",
            "7": "Продажа",
            "8": "Расторжение договора услуг",
            "9": "Юридическое сопровождение",
            "10": "Соглашение о расторжении аванса",
        }

        doc_type_name = doc_type_names.get(contract_data["doc_type"], "Неизвестный тип")

        # Если есть данные паспорта, используем их
        passport_data = contract_data.get("passport_data", {})
        if passport_data:
            message = f'Договор "{doc_type_name}" успешно сформирован!<br>'
            message += f'Данные риелтора: {passport_data.get("rieltor_first_name", "N/A")} {passport_data.get("rieltor_last_name", "N/A")}<br>'
            message += f'Данные клиента: {passport_data.get("client_first_name", "N/A")} {passport_data.get("client_last_name", "N/A")}<br><br>'
            message += "<strong>Внимание:</strong> Для полной функциональности необходимо интегрировать с системой генерации документов из бота."
        else:
            message = f'Договор "{doc_type_name}" успешно сформирован!<br>Данные риелтора и клиента обработаны.<br><br><strong>Внимание:</strong> Для полной функциональности необходимо интегрировать с системой генерации документов из бота.'

        return {
            "success": True,
            "message": message,
            "download_url": None,  # Здесь будет ссылка на скачивание сгенерированного договора
        }

    except Exception as e:
        return {"success": False, "message": f"Ошибка при генерации договора: {str(e)}"}


def _build_passport_payload_for_edit_link(user_id: int, doc_type: str) -> dict:
    """Собирает данные паспорта риелтора и последнего клиента (как в боте)."""
    rieltor_data = get_rieltor_data(user_id)
    client_data = get_last_client_data(user_id)
    if not rieltor_data or not client_data:
        return {}
    return {
        "doc_type": doc_type,
        "rieltor_last_name": rieltor_data["last_name"],
        "rieltor_first_name": rieltor_data["first_name"],
        "rieltor_middle_name": rieltor_data["middle_name"],
        "rieltor_birth_date": rieltor_data["birth_date"],
        "rieltor_passport_series": rieltor_data["passport_series"],
        "rieltor_passport_number": rieltor_data["passport_number"],
        "rieltor_issued_by": rieltor_data["issued_by"],
        "rieltor_issue_date": rieltor_data["issue_date"],
        "rieltor_registration_address": rieltor_data["registration_address"],
        "client_last_name": client_data["last_name"],
        "client_first_name": client_data["first_name"],
        "client_middle_name": client_data["middle_name"],
        "client_birth_date": client_data["birth_date"],
        "client_passport_series": client_data["passport_series"],
        "client_passport_number": client_data["passport_number"],
        "client_issued_by": client_data["issued_by"],
        "client_issue_date": client_data["issue_date"],
        "client_registration_address": client_data["registration_address"],
    }


async def send_passport_edit_link_web(user_id: int, token, payload: dict):

    body = {"token": token, "user_id": user_id, **payload}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            # TODO Вернуть старую ссылку после тестов
            # "http://localhost:8001/api/save_passport_data1",
            "https://neurochief.pro/api/save_passport_data1",
            json=body,
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                return {"success": False, "message": text}
    return {
        "success": True,
        # TODO Вернуть старую ссылку после тестов
        # "edit_url": f"http://localhost:8001/edit/{token}",
        "edit_url": f"https://neurochief.pro/edit/{token}",
    }


def async_login_required(view_func):
    async def _wrapped_view(request, *args, **kwargs):
        if not await sync_to_async(lambda: request.user.is_authenticated)():
            from django.shortcuts import redirect

            return redirect("telegram_login_redirect")
        return await view_func(request, *args, **kwargs)

    return _wrapped_view


def upload_passport_page(request, passport_type):
    """Страница загрузки фото паспорта (риелтора или клиента)"""
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    user_id = request.session.get("telegram_id")
    if not user_id:
        return redirect("telegram_login_redirect")

    # Проверяем права доступа
    banned = getBannedUserId(user_id)
    if banned != 0:
        context = {
            "title": "DomosClub",
            "page_title": "Доступ запрещен",
            "message": "Пользователь заблокирован!",
        }
        return render(request, "main_interface/access_denied.html", context)

    pay_status = getUserPay(user_id)
    if pay_status != 1:
        context = {
            "title": "DomosClub",
            "page_title": "Доступ запрещен",
            "message": "⭕ Сначала оплатите подписку!",
        }
        return render(request, "main_interface/access_denied.html", context)

    if passport_type not in ["rieltor", "client"]:
        context = {
            "title": "DomosClub",
            "page_title": "Ошибка",
            "message": "Неверный тип паспорта",
        }
        return render(request, "main_interface/access_denied.html", context)

    context = {
        "title": "DomosClub",
        "page_title": f"Загрузка паспорта {passport_type}",
        "passport_type": passport_type,
        "user_id": user_id,
    }

    template_name = "main_interface/upload_passport.html"
    return render(request, template_name, context)


def upload_passport_photo(request):
    """Обработка загрузки фото паспорта"""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Метод не поддерживается"})

    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    user_id = request.session.get("telegram_id")
    if not user_id:
        return redirect("telegram_login_redirect")

    try:
        passport_type = request.POST.get("passport_type")  # 'rieltor' или 'client'

        if not passport_type or passport_type not in ["rieltor", "client"]:
            return JsonResponse({"success": False, "message": "Неверный тип паспорта"})

        if "photo" not in request.FILES:
            return JsonResponse({"success": False, "message": "Фото не найдено"})

        photo = request.FILES["photo"]

        # Сохраняем файл
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_extension = os.path.splitext(photo.name)[1] or ".jpg"
        filename = f"{user_id}_{passport_type}_{timestamp}{file_extension}"

        # Создаем папку для паспортов если её нет
        passports_dir = os.path.join(BASE_DIR, "bot", "passports")
        os.makedirs(passports_dir, exist_ok=True)

        file_path = os.path.join(passports_dir, filename)

        with open(file_path, "wb") as f:
            for chunk in photo.chunks():
                f.write(chunk)
            f.flush()
            os.fsync(f.fileno())

            # Обрабатываем фото паспорта
            model = "passport"
            raw_text = vision_api.extract_text_from_image(file_path, model)

        if not raw_text:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Не удалось распознать текст. Попробуйте другое фото.",
                }
            )

        # Извлекаем структурированные данные паспорта
        passport_data = gpt_processor.extract_passport_data(raw_text)

        if not passport_data:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Не удалось извлечь данные паспорта. Попробуйте другое фото.",
                }
            )

        # Сохраняем данные в сессию для последующего сохранения в БД
        request.session[f"{passport_type}_passport_data"] = {
            "passport_data": passport_data,
            "photo_path": file_path,
        }

        return JsonResponse(
            {
                "success": True,
                "message": "Данные паспорта распознаны! Теперь загрузите фото страницы с регистрацией.",
                "next_step": "registration",
                "passport_data": passport_data,
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Ошибка при обработке: {str(e)}"}
        )


async def wait_for_signal_and_run_web(token: str) -> dict:
    """Ожидает изменения данных в веб-форме и возвращает обновлённые данные.

    Аналог функции ожидания из бота: циклично проверяет таблицу `tokens` в БД,
    и как только `Signal` станет 1 — читает `data_json`, сбрасывает сигнал и
    возвращает распарсенные данные.
    """
    while True:
        await asyncio.sleep(5)
        try:
            with sqlite3.connect(CONTRACT_TOKENS_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT Signal, data_json FROM tokens WHERE token = ?", (token,)
                )
                result = cursor.fetchone()

                if result:
                    signal, data_json = result
                    if signal == 1:
                        try:
                            passport_data = json.loads(data_json)
                            # Сбрасываем сигнал обратно в 0
                            cursor.execute(
                                "UPDATE tokens SET Signal = 0 WHERE token = ?", (token,)
                            )
                            conn.commit()
                            return {"success": True, "passport_data": passport_data}
                        except Exception as e:
                            logger_bot.error(
                                f"❌ Ошибка при обработке данных. Проверьте формат JSON: {e}"
                            )
                            cursor.execute(
                                "UPDATE tokens SET Signal = 0 WHERE token = ?", (token,)
                            )
                            conn.commit()
                            return {
                                "success": False,
                                "message": "Ошибка при обработке данных. Проверьте формат JSON.",
                            }
        except Exception as e:
            logger_bot.error(f"Ошибка при проверке сигнала: {e}")
            return {"success": False, "message": str(e)}


async def wait_for_signal_and_process_web(token: str, user_id: int, payload: dict):
    """Фоновая задача для ожидания изменений и обработки данных"""
    try:
        result = await wait_for_signal_and_run_web(token)
        if result.get("success"):
            # Генерируем договор, используя существующую функцию из бота
            try:

                class _FakeState:
                    async def get_data(self):
                        return {"doc_type": payload.get("doc_type")}

                passport_data = result["passport_data"]
                state = cast(FSMContext, _FakeState())
                # Создаём маркер процесса генерации, чтобы UI видел прогресс
                web_dir = os.path.join(BASE_DIR, "web", "contracts")
                os.makedirs(web_dir, exist_ok=True)
                processing_marker = os.path.join(web_dir, f"{token}.processing")
                try:
                    with open(processing_marker, "w") as mf:
                        mf.write("processing")
                except Exception as m_err:
                    logger_bot.error(f"Ошибка создания processing-маркера: {m_err}")

                output_path = await tg_generate_contract(
                    user_id,
                    passport_data,
                    state,
                )

                # Копируем/сохраняем файл под web-именем по token, чтобы отдать по ссылке
                web_path = os.path.join(web_dir, f"{token}.docx")

                try:
                    # Если путь уже тот же - просто оставим
                    if os.path.abspath(output_path) != os.path.abspath(web_path):
                        with open(output_path, "rb") as rf, open(web_path, "wb") as wf:
                            wf.write(rf.read())
                except Exception as copy_err:
                    logger_bot.error(f"Ошибка копирования договора для web: {copy_err}")
                finally:
                    # Удаляем маркер процесса
                    try:
                        if os.path.exists(processing_marker):
                            os.remove(processing_marker)
                    except Exception as rm_err:
                        logger_bot.error(
                            f"Ошибка удаления processing-маркера: {rm_err}"
                        )

                logger_bot.info(
                    f"✅ Договор сгенерирован для пользователя {user_id}, токен {token}: {web_path}"
                )
            except Exception as gen_err:
                logger_bot.exception(f"❌ Ошибка генерации договора (web): {gen_err}")
        else:
            logger_bot.error(f"❌ Ошибка при обработке данных: {result.get('message')}")
    except Exception as e:
        logger_bot.error(f"❌ Ошибка в фоновой задаче: {e}")


@csrf_exempt
def check_processing_status(request):
    """Эндпоинт для проверки статуса обработки данных"""
    if request.method != "GET":
        return JsonResponse({"success": False, "message": "Метод не поддерживается"})

    token = request.GET.get("token")
    if not token:
        return JsonResponse({"success": False, "message": "Токен не предоставлен"})

    try:
        with sqlite3.connect(CONTRACT_TOKENS_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT Signal, data_json FROM tokens WHERE token = ?", (token,)
            )
            result = cursor.fetchone()

            if not result:
                return JsonResponse(
                    {
                        "success": False,
                        "status": "not_found",
                        "message": "Токен не найден",
                    }
                )

            signal, data_json = result
            # Если файл уже сгенерирован - сообщаем URL
            contracts_dir = os.path.join(BASE_DIR, "web", "contracts")
            web_path = os.path.join(contracts_dir, f"{token}.docx")
            processing_marker = os.path.join(contracts_dir, f"{token}.processing")

            if os.path.exists(web_path):
                return JsonResponse(
                    {
                        "success": True,
                        "status": "completed",
                        "message": "Договор готов",
                        "file_url": reverse("download_contract", args=[token]),
                    }
                )

            # Если есть маркер обработки — договор генерируется
            if os.path.exists(processing_marker) or signal == 1:
                # Данные обновлены, договор в процессе генерации
                return JsonResponse(
                    {
                        "success": True,
                        "status": "processing",
                        "message": "Генерация договора...",
                    }
                )
            else:
                # Ожидание продолжается
                return JsonResponse(
                    {
                        "success": True,
                        "status": "waiting",
                        "message": "Ожидание обновления данных...",
                    }
                )

    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "status": "error",
                "message": f"Ошибка при проверке статуса: {str(e)}",
            }
        )


def download_contract(request, token: str):
    """Отдаёт сформированный договор по token в браузере"""
    web_path = os.path.join(BASE_DIR, "web", "contracts", f"{token}.docx")
    if not os.path.exists(web_path):
        raise Http404("Файл не найден")
    response = FileResponse(
        open(web_path, "rb"),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    response["Content-Disposition"] = f'inline; filename="{token}.docx"'
    return response


def upload_registration_photo(request):
    """Обработка загрузки фото страницы регистрации"""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Метод не поддерживается"})
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    user_id = request.session.get("telegram_id")
    if not user_id:
        return redirect("telegram_login_redirect")

    try:
        passport_type = request.POST.get("passport_type")  # 'rieltor' или 'client'

        if not passport_type or passport_type not in ["rieltor", "client"]:
            return JsonResponse({"success": False, "message": "Неверный тип паспорта"})

        # Проверяем, что данные паспорта уже загружены
        passport_session_key = f"{passport_type}_passport_data"
        if passport_session_key not in request.session:
            return JsonResponse(
                {"success": False, "message": "Сначала загрузите фото паспорта"}
            )

        if "photo" not in request.FILES:
            return JsonResponse({"success": False, "message": "Фото не найдено"})

        photo = request.FILES["photo"]

        # Сохраняем файл
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_extension = os.path.splitext(photo.name)[1] or ".jpg"
        filename = f"registration_{user_id}_{passport_type}_{timestamp}{file_extension}"

        # Создаем папку для паспортов если её нет
        passports_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "bot", "tgbot", "passports"
        )
        os.makedirs(passports_dir, exist_ok=True)

        file_path = os.path.join(passports_dir, filename)

        with open(file_path, "wb") as f:
            for chunk in photo.chunks():
                f.write(chunk)

        # Обрабатываем фото регистрации
        model = "handwritten"
        raw_text = vision_api.extract_text_from_image(file_path, model)

        if not raw_text:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Не удалось распознать текст регистрации. Попробуйте другое фото.",
                }
            )

        # Извлекаем данные регистрации
        registration_data = gpt_processor.extract_registration_data(raw_text)

        if not registration_data:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Не удалось извлечь данные регистрации. Попробуйте другое фото.",
                }
            )

        # Получаем данные паспорта из сессии
        passport_session_data = request.session[passport_session_key]
        passport_data = passport_session_data["passport_data"]

        # Сохраняем в базу данных
        if passport_type == "client":
            id1 = f"{user_id}_client"
            client_id = save_passport(
                passport_data, id1, registration_data, is_client=True
            )
        else:
            client_id = save_passport(
                passport_data, user_id, registration_data, is_client=False
            )

        # Очищаем сессию
        del request.session[passport_session_key]

        # Определяем следующий шаг
        if passport_type == "rieltor":
            # Если загружали паспорт риелтора, проверяем клиента
            client_exists = check_passport_client_exists(user_id)
            if client_exists == 1:
                next_step = "upload_client_passport"
                message = "Данные риелтора сохранены! Теперь загрузите паспорт клиента."
            else:
                next_step = "contract_menu"
                message = "Данные риелтора сохранены! Можно формировать договоры."
        else:
            # Если загружали паспорт клиента, возвращаемся к меню договоров
            next_step = "contract_menu"
            message = "Данные клиента сохранены! Можно формировать договоры."

        return JsonResponse(
            {
                "success": True,
                "message": message,
                "next_step": next_step,
                "client_id": client_id,
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Ошибка при обработке: {str(e)}"}
        )
