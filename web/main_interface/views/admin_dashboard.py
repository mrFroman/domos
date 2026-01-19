import os
import requests
from datetime import datetime

from django.core.files.storage import default_storage
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from bot.tgbot.databases.pay_db import (
    banUser,
    checkUserExistsUsername,
    createContact,
    createRieltor,
    changeUserAdmin,
    getAllUsersForAd,
    getBannedUserId,
    getFreeUsersCount,
    getFreeUsersForAd,
    getPaidUsers,
    getPaidUsersCount,
    getPaidUsersForAd,
    getUserEndPay,
    getUsersCount,
    giveUserSub,
    takeUserSub,
    unbanUser,
    sendLogToUser,
)
from bot.tgbot.keyboards.inline import get_random_string
from bot.tgbot.handlers.advert_admin import (
    load_advert_positions,
    save_advert_positions,
)
from bot.tgbot.misc.exunpaid import (
    create_excel_advert,
    create_excel_advert_new,
    create_excel,
    create_excel1,
    create_excel_lawyer,
)
from config import BASE_DIR, load_config


config = load_config()
PLACEHOLDER_DESCRIPTION = "Раздел в разработке. Следите за обновлениями DomosClub."


def admin_analytics(request):
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    paid_count = getPaidUsersCount()
    free_count = getFreeUsersCount()
    allint_count = getUsersCount()
    msg = f"""Всего людей в боте: {allint_count}
Оплачено: {paid_count}
Бесплатно: {free_count}

Ниже список платных пользователей:
"""
    paid_users = getPaidUsers()
    context = {
        "title": "DomosClub",
        "page_title": "Аналитика",
        "msg": msg,
        "paid_users": paid_users,
    }
    return render(
        request,
        "main_interface/admin/admin_analytics.html",
        context,
    )


def admin_broadcast(request):
    context = {
        "title": "DomosClub",
        "page_title": "Сделать рассылку",
    }

    if request.method == "POST":
        adtype = request.POST.get("adtype")
        text = request.POST.get("text")
        photo = request.FILES.get("photo")

        if not text:
            request.session["error"] = "Введите текст рассылки."
            return redirect(reverse("admin_broadcast"))

        # Заглушки: здесь должен быть твой код выборки пользователей
        if adtype == "all":
            users = getAllUsersForAd()
        elif adtype == "paid":
            users = getPaidUsersForAd()
        else:
            users = getFreeUsersForAd()

        # Фото сохраняем временно (если есть)
        photo_path = None
        if photo:
            photo_path = default_storage.save(f"broadcast/{photo.name}", photo)

        # Логика отправки (упрощённо)
        for user_id in users:
            if photo_path:
                url = f"https://api.telegram.org/bot{config.tg_bot.token}/sendPhoto"

                with open(
                    os.path.join(BASE_DIR, "web", "media", "broadcast", photo.name),
                    "rb",
                ) as photo:
                    files = {"photo": photo}
                    data = {
                        "chat_id": user_id,
                        "caption": text,
                        "parse_mode": "HTML",
                    }
                    r = requests.post(url, data=data, files=files)
                # return r.status_code == 200
            else:
                sendLogToUser(text, user_id[0])

        request.session["success"] = "Рассылка выполнена."
        return redirect(reverse("admin_broadcast"))

    context["error"] = request.session.pop("error", None)
    context["success"] = request.session.pop("success", None)

    return render(
        request,
        "main_interface/admin/admin_broadcast.html",
        context,
    )


def admin_find_user(request):
    ctx = {
        "title": "DomosClub",
        "page_title": "Управление пользователем",
        "result": None,
        "message": None,
    }

    # Когда форма ещё не отправлена
    if request.method != "POST":
        return render(request, "main_interface/admin/admin_find_user.html", ctx)

    action = request.POST.get("action")    # какое действие? search / ban / unban / makesub / takesub / giverole / give_months
    username = request.POST.get("username")
    user_id = request.POST.get("user_id")

    # 1) Поиск пользователя
    if action == "search":
        if not username:
            ctx["message"] = "Введите username"
            return render(request, "main_interface/admin/admin_find_user.html", ctx)

        user_id, pay_status, rank, username = checkUserExistsUsername(username)

        if user_id == "empty":
            ctx["message"] = "Пользователь не найден"
            return render(request, "main_interface/admin/admin_find_user.html", ctx)

        result = {"user_id": user_id, "username": username}

        # Статус оплаты
        if int(pay_status) == 1:
            endts = float(getUserEndPay(user_id))
            enddate = datetime.fromtimestamp(endts)
            result["pay_status"] = f"Оплачено до {enddate}"
        else:
            result["pay_status"] = "Не оплачено"

        # Ранг
        result["rank"] = "Админ" if int(rank) == 1 else "Юзер"

        # Бан
        banned = getBannedUserId(user_id)
        result["banned"] = "Забанен" if banned == 1 else "Не забанен"

        ctx["result"] = result
        return render(request, "main_interface/admin/admin_find_user.html", ctx)

    # 2) Бан
    if action == "ban" and user_id:
        banUser(user_id)
        ctx["message"] = "Пользователь забанен"
        return render(request, "main_interface/admin/admin_find_user.html", ctx)

    # 3) Разбан
    if action == "unban" and user_id:
        unbanUser(user_id)
        ctx["message"] = "Пользователь разбанен"
        return render(request, "main_interface/admin/admin_find_user.html", ctx)

    # 4) Отобрать подписку
    if action == "take_sub" and user_id:
        takeUserSub(user_id)
        ctx["message"] = "Подписка отключена"
        return render(request, "main_interface/admin/admin_find_user.html", ctx)

    # 5) Сделать/разжаловать админа
    if action == "toggle_admin" and user_id:
        res = changeUserAdmin(user_id)
        ctx["message"] = "Пользователь стал админом" if res == "admined" else "Пользователь разжалован"
        return render(request, "main_interface/admin/admin_find_user.html", ctx)

    # 6) Дать подписку на N месяцев
    if action == "give_months" and user_id:
        months = int(request.POST.get("months", 0))
        if months <= 0:
            ctx["message"] = "Введите корректное количество месяцев"
        else:
            giveUserSub(user_id, months)
            ctx["message"] = "Подписка успешно выдана"
        return render(request, "main_interface/admin/admin_find_user.html", ctx)

    return render(request, "main_interface/admin/admin_find_user.html", ctx)


def admin_unpaid(request):
    create_excel()

    file_path = os.path.join(BASE_DIR, "bot", "tgbot", "misc", "dataunpaids.xlsx")

    if not os.path.exists(file_path):
        return HttpResponse("Файл не найден", status=500)

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename="dataunpaids.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def admin_paid(request):
    create_excel1()
    file_path = os.path.join(BASE_DIR, "bot", "tgbot", "misc", "datapaids.xlsx")
    if not os.path.exists(file_path):
        return HttpResponse("Файл не найден", status=500)

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename="datapaids.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def admin_legal_requests(request):
    create_excel_lawyer()
    file_path = os.path.join(BASE_DIR, "bot", "tgbot", "misc", "lawyer.xlsx")
    if not os.path.exists(file_path):
        return HttpResponse("Файл не найден", status=500)

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename="lawyer.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def admin_advert_requests(request):
    create_excel_advert()
    file_path = os.path.join(BASE_DIR, "bot", "tgbot", "misc", "advert.xlsx")
    if not os.path.exists(file_path):
        return HttpResponse("Файл не найден", status=500)

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename="advert.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def admin_advert_queries(request):
    file_path = create_excel_advert_new()
    if not os.path.exists(file_path):
        return HttpResponse("Файл не найден", status=500)

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename="advert_report.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def admin_advert_management(request):
    context = {
        "title": "DomosClub",
        "page_title": "Управление рекламой",
    }

    action = request.GET.get("action", "list")  # list / add / edit / delete
    positions = load_advert_positions()
    context["action"] = action

    if action == "list":
        context["positions"] = positions
        return render(
            request, "main_interface/admin/admin_advert_management.html", context
        )

    if action == "add":
        if request.method == "POST":
            name = request.POST.get("name")
            price = request.POST.get("price")

            if not name:
                context["error"] = "Название не может быть пустым."
                return render(
                    request,
                    "main_interface/admin/admin_advert_management.html",
                    context,
                )

            if len(name) > 100:
                context["error"] = "Название слишком длинное (максимум 100 символов)."
                return render(
                    request,
                    "main_interface/admin/admin_advert_management.html",
                    context,
                )

            try:
                price = float(price)
                if price < 0:
                    raise ValueError
            except ValueError:
                context["error"] = "Введите корректную цену."
                return render(
                    request,
                    "main_interface/admin/admin_advert_management.html",
                    context,
                )

            existing_keys = [p["key"] for p in positions]
            base_key = "".join(c.lower() for c in name if c.isalnum())[:20]
            key = base_key
            counter = 1
            while key in existing_keys:
                key = f"{base_key}_{counter}"
                counter += 1

            positions.append({"key": key, "name": name, "price": price})
            save_advert_positions(positions)

            context["success"] = f"Позиция '{name}' успешно добавлена."
            context["positions"] = positions
            context["action_done"] = True
            return render(
                request, "main_interface/admin/admin_advert_management.html", context
            )

        return render(
            request, "main_interface/admin/admin_advert_management.html", context
        )

    if action == "edit":
        index = request.GET.get("index")
        if index is None:
            return redirect(reverse("admin_advert_management"))

        try:
            index = int(index)
            position = positions[index]
        except Exception:
            return redirect(reverse("admin_advert_management"))

        context["edit_position"] = position
        context["index"] = index

        if request.method == "POST":
            name = request.POST.get("name")
            price = request.POST.get("price")

            if not name:
                context["error"] = "Название не может быть пустым."
                return render(
                    request,
                    "main_interface/admin/admin_advert_management.html",
                    context,
                )

            if len(name) > 100:
                context["error"] = "Название слишком длинное."
                return render(
                    request,
                    "main_interface/admin/admin_advert_management.html",
                    context,
                )

            try:
                price = float(price)
                if price < 0:
                    raise ValueError
            except ValueError:
                context["error"] = "Введите корректную цену."
                return render(
                    request,
                    "main_interface/admin/admin_advert_management.html",
                    context,
                )

            positions[index]["name"] = name
            positions[index]["price"] = price
            save_advert_positions(positions)

            context["success"] = "Изменения сохранены."
            context["positions"] = positions
            context["action_done"] = True
            return render(
                request, "main_interface/admin/admin_advert_management.html", context
            )

        return render(
            request, "main_interface/admin/admin_advert_management.html", context
        )

    if action == "delete":
        index = request.GET.get("index")
        if index is None:
            return redirect(reverse("admin_advert_management"))

        try:
            index = int(index)
            position = positions[index]
        except Exception:
            return redirect(reverse("admin_advert_management"))

        context["delete_position"] = position
        context["index"] = index

        if request.method == "POST":
            positions.pop(index)
            save_advert_positions(positions)

            context["success"] = "Позиция удалена."
            context["positions"] = positions
            context["action_done"] = True
            return render(
                request, "main_interface/admin/admin_advert_management.html", context
            )

        return render(
            request, "main_interface/admin/admin_advert_management.html", context
        )

    context["positions"] = positions
    return render(request, "main_interface/admin/admin_advert_management.html", context)


def admin_feedback_table(request):
    return redirect(
        "https://docs.google.com/spreadsheets/d/17_deblA-6h1tWD4FHoo0n7DNrt44UA6j36daYj0Nl64/edit?usp=sharing"
    )


def admin_add_realtor(request):
    context = {
        "title": "DomosClub",
        "page_title": "Добавить риэлтора",
    }

    if request.method == "POST":
        fullname = request.POST.get("fullname")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        photo = request.FILES.get("photo")

        # Валидация
        if not fullname:
            context["error"] = "Введите ФИО."
            return render(
                request, "main_interface/admin/admin_add_realtor.html", context
            )

        if not phone:
            context["error"] = "Введите номер телефона."
            return render(
                request, "main_interface/admin/admin_add_realtor.html", context
            )

        if not email:
            context["error"] = "Введите email."
            return render(
                request, "main_interface/admin/admin_add_realtor.html", context
            )

        if not photo:
            context["error"] = "Загрузите фото риэлтора."
            return render(
                request, "main_interface/admin/admin_add_realtor.html", context
            )

        # Сохраняем фото
        photo_path = default_storage.save(f"realtors/{photo.name}", photo)

        # Создаём риэлтора
        rieltor_id = get_random_string(7)
        createRieltor(
            rieltor_id=rieltor_id,
            fullname=fullname,
            email=email,
            photo=photo_path,
            phone=phone,
        )

        context["success"] = "Риэлтор успешно добавлен!"
        return render(request, "main_interface/admin/admin_add_rieltor.html", context)

    return render(request, "main_interface/admin/admin_add_rieltor.html", context)


def admin_add_contact(request):
    context = {
        "title": "DomosClub",
        "page_title": "Добавить контакт",
    }

    if request.method == "POST":
        fullname = request.POST.get("fullname")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        job = request.POST.get("job")
        photo = request.FILES.get("photo")

        # Валидация
        if not fullname:
            context["error"] = "Введите ФИО."
            return render(
                request, "main_interface/admin/admin_add_contact.html", context
            )

        if not phone:
            context["error"] = "Введите номер телефона."
            return render(
                request, "main_interface/admin/admin_add_contact.html", context
            )

        if not email:
            context["error"] = "Введите email."
            return render(
                request, "main_interface/admin/admin_add_contact.html", context
            )

        if not photo:
            context["error"] = "Загрузите фото."
            return render(
                request, "main_interface/admin/admin_add_contact.html", context
            )

        if not job:
            context["error"] = "Введите должность."
            return render(
                request, "main_interface/admin/admin_add_contact.html", context
            )

        # Сохраняем фото
        photo_path = default_storage.save(f"contacts/{photo.name}", photo)

        # Создаём контакт
        contact_id = get_random_string(7)
        createContact(
            contact_id=contact_id,
            fullname=fullname,
            phone=phone,
            email=email,
            photo=photo_path,
            job=job,
        )

        context["success"] = "Контакт успешно добавлен!"
        return render(request, "main_interface/admin/admin_add_contact.html", context)

    return render(request, "main_interface/admin/admin_add_contact.html", context)
