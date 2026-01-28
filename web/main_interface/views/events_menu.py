from datetime import datetime

from django.shortcuts import render, redirect

from bot.tgbot.databases.pay_db import getEvents, getEventId


def events_menu(request):
    if not request.user.is_authenticated:
        print(request.user.is_authenticated)
        return redirect("telegram_login_redirect")

    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    now = datetime.now().timestamp()
    events = getEvents()
    out_events = []
    for event in events:
        # Поддержка как словаря (PostgreSQL), так и кортежа (SQLite)
        if isinstance(event, dict):
            event_date = event.get("date", 0)
            event_id = event.get("event_id", 0)
            event_title = event.get("title", "")
            event_name = event.get("name", "")
        else:
            event_date = event[2]
            event_id = event[0]
            event_title = event[3]
            event_name = event[5]
        
        try:
            event_date = float(event_date) if event_date else 0
        except (ValueError, TypeError):
            event_date = 0
            
        if event_date < now:  # если дата события меньше текущего времени
            continue
        dt_object = datetime.fromtimestamp(event_date).strftime("%d-%m-%Y %H:%M")
        out_events.append(
            {
                "id": event_id,
                "title": event_title,
                "name": event_name,
                "date": dt_object,
                "display_text": f"{event_title} [{dt_object}]",
            }
        )

    context = {
        "title": "DomosClub",
        "page_title": "Мероприятия",
        "events": out_events,
    }
    return render(request, "main_interface/events/events.html", context)


def event_detail(request, event_id):
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    event = getEventId(event_id)
    if not event:
        return redirect("events_menu")

    # Поддержка как словаря (PostgreSQL), так и кортежа (SQLite)
    if isinstance(event, dict):
        e_id = event.get("event_id", 0)
        e_desc = event.get("desc", "")
        e_date = event.get("date", 0)
        e_title = event.get("title", "")
        e_link = event.get("link", "")
        e_name = event.get("name", "")
        e_photo = event.get("photo", "")
    else:
        e_id = event[0]
        e_desc = event[1]
        e_date = event[2]
        e_title = event[3]
        e_link = event[4]
        e_name = event[5]
        e_photo = event[6]

    try:
        e_date = float(e_date) if e_date else 0
    except (ValueError, TypeError):
        e_date = 0
    dt_object = datetime.fromtimestamp(e_date).strftime("%d-%m-%Y %H:%M")

    # Проверяем, является ли photo валидным URL (не file_id)
    photo = e_photo
    if photo and photo != "0" and not photo.startswith("http"):
        photo = None  # file_id не подходит для веб-интерфейса

    context = {
        "title": "DomosClub",
        "page_title": e_name if e_name else e_title,
        "event": {
            "id": e_id,
            "title": e_title,
            "name": e_name,
            "description": e_desc,
            "date": dt_object,
            "link": e_link,
            "photo": photo,
        },
    }
    return render(request, "main_interface/events/event_detail.html", context)
