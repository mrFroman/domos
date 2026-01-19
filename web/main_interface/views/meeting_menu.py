import calendar
import os
import sys
from datetime import date, datetime

from django.shortcuts import render, redirect
from django.utils.crypto import get_random_string

BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        os.pardir,
        os.pardir,
    )
)
sys.path.append(BASE_DIR)

from bot.tgbot.databases.pay_db import (  # noqa: E402
    checkTimeExists1,
    createMeeting,
    deleteMeeting,
    editTimes,
    get_user_by_user_id,
    makeMeetCompleted,
)
from web.main_interface.utils import generate_time_slots  # noqa: E402


months = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


def _extract_telegram_id(django_user):
    if hasattr(django_user, "telegram_id") and django_user.telegram_id:
        return int(django_user.telegram_id)

    username = getattr(django_user, "username", "")
    digits = "".join(filter(str.isdigit, username or ""))
    if digits:
        return int(digits)
    return None


def meeting_booking(request):
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    telegram_id = _extract_telegram_id(request.user)
    if not telegram_id:
        return redirect("telegram_login_redirect")

    user = get_user_by_user_id(telegram_id)
    if not user:
        return redirect("telegram_login_redirect")

    step = request.GET.get("step", "floor")
    floornum = request.POST.get("floornum") or request.GET.get("floornum")
    roomnum = request.POST.get("roomnum") or request.GET.get("roomnum")
    meeting_day = request.POST.get("meeting_day") or request.GET.get("meeting_day")
    selected_time = request.POST.get("time") or request.GET.get("time")

    booking_result = None

    # Получаем текущий месяц и год
    current_year = int(request.GET.get("year", date.today().year))
    current_month = int(request.GET.get("month", date.today().month))

    # Вычисляем предыдущий и следующий месяц и год
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year

    if current_month == 12:
        next_month = 1
        next_year = current_year + 1
    else:
        next_month = current_month + 1
        next_year = current_year

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(current_year, current_month)

    occupied_slots = {}
    if meeting_day and roomnum:
        try:
            occupied_slots = checkTimeExists1(meeting_day, int(roomnum))
        except Exception:
            occupied_slots = {}

    time_slots = []
    for slot in generate_time_slots():
        occupant = occupied_slots.get(slot)
        time_slots.append(
            {
                "value": slot,
                "label": slot if not occupant else f"{slot} (@{occupant})",
                "is_busy": bool(occupant),
            }
        )

    meeting_day_display = None
    if meeting_day:
        try:
            parsed_day = datetime.strptime(meeting_day, "%d/%m/%Y")
            meeting_day_display = parsed_day.strftime("%d.%m.%Y")
        except ValueError:
            meeting_day_display = meeting_day

    if request.method == "POST":
        if not all([floornum, roomnum, meeting_day, selected_time]):
            booking_result = {
                "status": "error",
                "message": (
                    "Не удалось определить параметры бронирования. "
                    "Попробуйте ещё раз."
                ),
            }
        elif occupied_slots.get(selected_time):
            booking_result = {
                "status": "error",
                "message": (
                    "Данное время уже занято. " "Пожалуйста, выберите другой слот."
                ),
            }
        else:
            meeting_id = get_random_string(8)
            createMeeting(telegram_id, meeting_day, meeting_id, roomnum)
            save_result = editTimes(
                meeting_id,
                f"{selected_time};",
                int(roomnum),
            )
            if save_result == "busied":
                deleteMeeting(meeting_id)
                booking_result = {
                    "status": "error",
                    "message": ("Не удалось забронировать: слот только что заняли."),
                }
            else:
                makeMeetCompleted(
                    meeting_id,
                    user.get("username") or getattr(request.user, "username", ""),
                    int(roomnum),
                )
                booking_result = {
                    "status": "success",
                    "message": (
                        "Переговорная забронирована на "
                        f"{meeting_day_display} в {selected_time}."
                    ),
                }
                step = "confirm"

    context = {
        "user": user,
        "step": step,
        "floornum": floornum,
        "roomnum": roomnum,
        "meeting_day": meeting_day,
        "meeting_day_display": meeting_day_display,
        "prev_month": prev_month,
        "prev_year": prev_year,
        "current_month": months[current_month],
        "current_month_num": current_month,
        "current_year": current_year,
        "next_month": next_month,
        "next_year": next_year,
        "calendar_weeks": month_days,
        "available_slots": time_slots,
        "time": selected_time,
        "booking_result": booking_result,
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(
            request,
            "main_interface/meeting/meeting_booking_partial.html",
            context,
        )
    return render(
        request,
        "main_interface/meeting/meeting_booking.html",
        context,
    )
