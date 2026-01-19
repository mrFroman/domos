from django.shortcuts import render, redirect

MAIN_TEXT = """Хочется получить бесплатный месяц? Не проблема — просто пригласите коллег.

Пришлите им приглашение с индивидуальной реферальной ссылкой. Для этого нужно отправить вашу ссылку другу, бот отправил вам ее вторым сообщением

Как только приглашенный вами друг оплатит месяц договора вы получите месяц бесплатно"""


def invite_menu(request):
    if not request.user.is_authenticated:
        print(request.user.is_authenticated)
        return redirect("telegram_login_redirect")

    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    invite_link = f'https://t.me/DomosproBot?start={request_user.split("_")[1]}'

    context = {
        "title": "DomosClub",
        "page_title": "Пригласи друга",
        "main_text": MAIN_TEXT,
        "invite_link": invite_link,
    }
    return render(request, "main_interface/invite/invite.html", context)
