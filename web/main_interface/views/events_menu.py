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
        if event[2] < now:  # если дата события меньше текущего времени
            continue
        dt_object = datetime.fromtimestamp(event[2]).strftime("%d-%m-%Y %H:%M")
        out_events.append(
            {
                "id": event[0],  # event_id
                "title": event[3],  # title
                "name": event[5],  # name
                "date": dt_object,
                "display_text": f"{event[3]} [{dt_object}]",
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

    # Структура события: event[0]=id, event[1]=desc, event[2]=date,
    # event[3]=title, event[4]=link, event[5]=name, event[6]=photo
    dt_object = datetime.fromtimestamp(event[2]).strftime("%d-%m-%Y %H:%M")

    # Проверяем, является ли photo валидным URL (не file_id)
    photo = event[6]
    if photo and photo != "0" and not photo.startswith("http"):
        photo = None  # file_id не подходит для веб-интерфейса

    context = {
        "title": "DomosClub",
        "page_title": event[5] if event[5] else event[3],
        "event": {
            "id": event[0],
            "title": event[3],
            "name": event[5],
            "description": event[1],
            "date": dt_object,
            "link": event[4],
            "photo": photo,
        },
    }
    return render(request, "main_interface/events/event_detail.html", context)
