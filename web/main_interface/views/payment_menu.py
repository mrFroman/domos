import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)

from django.http import FileResponse, JsonResponse
from django.shortcuts import render, redirect

from bot.tgbot.databases.pay_db import (
    get_user_by_user_id,
    createPayment,
    getPayment,
    update_user_full_name,
)
from bot.tgbot.handlers.payment import create_payment1
from config import BASE_DIR


def payment_menu(request):
    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    telegram_id = int("".join(filter(str.isdigit, request_user)))
    user = get_user_by_user_id(telegram_id)
    step = request.GET.get("step", "period")

    period = request.GET.get("period", None)
    if period == "month":
        price = 10000
    elif period == "open":
        price = 12900
    elif period == "three":
        price = 30000
    elif period == "halfyear":
        price = 60000
    elif period == "year":
        price = 108000
    elif period == "test":
        price = 1
    else:
        price = 0

    name = request.GET.get("name", None)
    if name is None:
        name = ""
        payment_id = None
        payment_link = None
    else:
        if step != "check_payment":
            payment_id, payment_link = create_payment1(price, "Покупка подписки", name)
            createPayment(payment_id, price, telegram_id)
            update_user_full_name(telegram_id, name)
        else:
            payment_id = request.GET.get("payment_id")
            payment_link = request.GET.get("payment_link")

    pay_status = user["pay_status"]
    end_pay = user["end_pay"]

    context = {
        "user": user,
        "step": step,
        "period": period,
        "price": price,
        "payment_id": payment_id,
        "payment_link": payment_link,
        "username": user["fullName"],
        "user_id": int(user["user_id"]),
        "title": "DomosClub",
        "menu_lable": "Дата окончания подписки:",
        "pay_status": pay_status,
        "end_pay": end_pay,
    }
    return render(request, "main_interface/payment/payment.html", context)


def download_offer(request):
    file_path = os.path.join(BASE_DIR, "bot", "tgbot", "Оферта_ЦН_Домос.docx")
    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename="Оферта_ЦН_Домос.docx",
    )


def payment_sub_check(request, payment_id):
    _, _, _, status = getPayment(payment_id)
    print(f"{status=}")
    return JsonResponse({"status": status})
