from django.shortcuts import render, redirect


def rules_menu(request):
    request_user = str(request.user)
    if not request_user:
        return redirect("telegram_login_redirect")

    context = {
        "title": "Правила DomosClub",
        "page_title": "Правила DomosClub",
    }
    return render(request, "main_interface/rules/rules.html", context)
