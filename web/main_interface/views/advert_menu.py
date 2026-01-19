import uuid
import logging
import asyncio
import aiohttp
from django.shortcuts import render, redirect

logger = logging.getLogger(__name__)


async def _call_save_advert_data(payload):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            # TODO Вернуть после тестов
            "http://localhost:8001/api/save_advert_data",
            # "https://neurochief.pro/api/save_advert_data",
            json=payload,
            timeout=5,
        ) as resp:
            return resp.status, await resp.text()


def advert_menu(request):
    if not request.user.is_authenticated:
        return redirect("telegram_login_redirect")

    user_id = str(request.user).split("_")[1]
    print(f'{user_id=}')
    token = uuid.uuid4().hex

    payload = {
        "user_id": int(user_id),
        "token": token,
    }

    # Асинхронный вызов aiohttp внутри синхронного Django view
    try:
        status, text = asyncio.run(_call_save_advert_data(payload))

        if status != 200:
            logger.error(f"Ошибка API save_advert_data: {text}")
            return render(
                request,
                "main_interface/advert/advert.html",
                {
                    "title": "DomosClub",
                    "page_title": "Заявка на рекламу",
                    "error": "Не удалось сформировать ссылку для заявки на рекламу",
                },
            )

    except Exception as exc:
        logger.exception(f"Ошибка aiohttp: {exc}")
        return render(
            request,
            "main_interface/advert/advert.html",
            {
                "title": "DomosClub",
                "page_title": "Заявка на рекламу",
                "error": str(exc),
            },
        )
    # TODO Вернуть после тестов
    form_url = f"http://localhost:8001/api/send_advert_form/{token}"
    # form_url = f"https://neurochief.pro/api/send_advert_form/{token}"

    return render(
        request,
        "main_interface/advert/advert.html",
        {
            "title": "DomosClub",
            "page_title": "Заявка на рекламу",
            "form_url": form_url,
            "description": (
                "В данной форме нужно указать количество необходимых вам размещений."
            ),
        },
    )
