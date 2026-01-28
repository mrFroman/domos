"""
Views для авторизации по номеру телефона с кодом подтверждения через Telegram бота
"""
import logging
import re

from django.contrib.auth import login as django_login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from web.main_interface.models import PhoneAuthCode
from web.main_interface.utils.telegram_sender import send_code_to_user, find_telegram_id_by_phone

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """
    Нормализует номер телефона к единому формату
    
    Args:
        phone: Номер телефона в любом формате
    
    Returns:
        str: Нормализованный номер телефона (только цифры)
    """
    # Убираем все кроме цифр
    phone_clean = ''.join(filter(str.isdigit, phone))
    
    # Если номер начинается с 8, заменяем на 7
    if phone_clean.startswith('8'):
        phone_clean = '7' + phone_clean[1:]
    
    # Если номер начинается с +7, убираем +
    if phone_clean.startswith('7') and len(phone_clean) == 11:
        return phone_clean
    
    # Если номер из 10 цифр, добавляем 7
    if len(phone_clean) == 10:
        return '7' + phone_clean
    
    return phone_clean


def validate_phone(phone: str) -> bool:
    """
    Проверяет валидность номера телефона
    
    Args:
        phone: Номер телефона
    
    Returns:
        bool: True если номер валиден
    """
    phone_clean = normalize_phone(phone)
    # Российский номер должен быть 11 цифр (7XXXXXXXXXX)
    return len(phone_clean) == 11 and phone_clean.startswith('7')


@require_http_methods(["GET", "POST"])
def phone_login(request):
    """
    Страница ввода номера телефона для авторизации
    """
    if request.user.is_authenticated:
        from django.urls import reverse
        return redirect(reverse("main_menu"))
    
    error_message = None
    
    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        
        if not phone:
            error_message = "Пожалуйста, введите номер телефона"
        elif not validate_phone(phone):
            error_message = "Неверный формат номера телефона. Используйте формат: +7XXXXXXXXXX или 8XXXXXXXXXX"
        else:
            phone_normalized = normalize_phone(phone)
            
            # Ищем пользователя в базе данных по номеру телефона
            telegram_user_id = find_telegram_id_by_phone(phone_normalized)
            
            if not telegram_user_id:
                # Сохраняем номер телефона в сессии для возможного использования
                request.session["phone_auth_phone"] = phone_normalized
                # Перенаправляем на страницу ввода Telegram ID/username
                return redirect("phone_enter_telegram_id")
            else:
                # Создаем код подтверждения
                auth_code = PhoneAuthCode.create_code(phone_normalized)
                # Сохраняем telegram_user_id в коде сразу
                auth_code.telegram_user_id = telegram_user_id
                auth_code.save()
                
                # Отправляем код через Telegram бота
                success = send_code_to_user(phone_normalized, auth_code.code, telegram_user_id)
                
                if success:
                    # Сохраняем номер телефона в сессии
                    request.session["phone_auth_phone"] = phone_normalized
                    request.session["phone_auth_code_id"] = auth_code.id
                    
                    logger.info(f"Код отправлен пользователю {telegram_user_id} для номера {phone_normalized}")
                    return redirect("phone_verify_code")
                else:
                    error_message = (
                        "Не удалось отправить код подтверждения. "
                        "Проверьте, что вы подписаны на Telegram бота и попробуйте еще раз."
                    )
    
    return render(
        request,
        "auth/phone_login.html",
        {
            "error_message": error_message,
        },
    )


@require_http_methods(["GET", "POST"])
def phone_enter_telegram_id(request):
    """
    Страница ввода Telegram ID или username, если номер телефона не найден
    """
    if request.user.is_authenticated:
        from django.urls import reverse
        return redirect(reverse("main_menu"))
    
    phone = request.session.get("phone_auth_phone")
    if not phone:
        from django.urls import reverse
        return redirect(reverse("phone_login"))
    
    error_message = None
    
    if request.method == "POST":
        telegram_input = request.POST.get("telegram_id", "").strip()
        
        if not telegram_input:
            error_message = "Пожалуйста, введите Telegram ID или username"
        else:
            # Пробуем определить, это ID (только цифры) или username (начинается с @)
            telegram_user_id = None
            
            if telegram_input.isdigit():
                # Это ID
                telegram_user_id = int(telegram_input)
            elif telegram_input.startswith('@'):
                # Это username, нужно найти ID по username
                telegram_user_id = find_telegram_id_by_username(telegram_input[1:])
            else:
                # Пробуем как ID
                try:
                    telegram_user_id = int(telegram_input)
                except ValueError:
                    # Пробуем как username без @
                    telegram_user_id = find_telegram_id_by_username(telegram_input)
            
            if not telegram_user_id:
                error_message = (
                    "Не удалось найти пользователя с таким Telegram ID или username. "
                    "Убедитесь, что вы зарегистрированы в Telegram боте."
                )
            else:
                # Создаем код подтверждения
                auth_code = PhoneAuthCode.create_code(phone)
                auth_code.telegram_user_id = telegram_user_id
                auth_code.save()
                
                # Отправляем код через Telegram бота
                success = send_code_to_user(phone, auth_code.code, telegram_user_id)
                
                if success:
                    request.session["phone_auth_code_id"] = auth_code.id
                    logger.info(f"Код отправлен пользователю {telegram_user_id} для номера {phone}")
                    return redirect("phone_verify_code")
                else:
                    error_message = (
                        "Не удалось отправить код подтверждения. "
                        "Проверьте, что вы подписаны на Telegram бота и попробуйте еще раз."
                    )
    
    return render(
        request,
        "auth/phone_enter_telegram_id.html",
        {
            "phone": phone,
            "error_message": error_message,
        },
    )


def find_telegram_id_by_username(username: str):
    """
    Найти Telegram ID по username
    """
    import sys
    import os
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    
    try:
        from bot.tgbot.databases.database import DatabaseConnection
        from config import MAIN_DB_PATH, DB_TYPE
        
        schema = "main" if DB_TYPE == "postgres" else None
        db = DatabaseConnection(MAIN_DB_PATH, schema=schema)
        
        if DB_TYPE == "postgres":
            query = "SELECT user_id FROM main.users WHERE username = %s LIMIT 1"
            result = db.fetchone(query, (username,))
        else:
            query = "SELECT user_id FROM users WHERE username = ? LIMIT 1"
            result = db.fetchone(query, (username,))
        
        if result:
            user_id = result.get('user_id') if isinstance(result, dict) else result[0]
            if user_id:
                logger.info(f"Найден пользователь по username: user_id={user_id}, username={username}")
                return int(user_id)
        
        return None
    except Exception as e:
        logger.error(f"Ошибка при поиске пользователя по username: {e}")
        return None


@require_http_methods(["GET", "POST"])
def phone_verify_code(request):
    """
    Страница ввода кода подтверждения
    """
    if request.user.is_authenticated:
        from django.urls import reverse
        return redirect(reverse("main_menu"))
    
    phone = request.session.get("phone_auth_phone")
    code_id = request.session.get("phone_auth_code_id")
    
    # Если нет данных в сессии, редиректим на страницу входа
    if not phone:
        # Очищаем сессию, чтобы избежать циклов
        request.session.flush()
        from django.urls import reverse
        return redirect(reverse("phone_login"))
    
    # Если нет code_id, но есть phone, пробуем найти последний код
    if not code_id:
        try:
            from web.main_interface.models import PhoneAuthCode
            last_code = PhoneAuthCode.objects.filter(
                phone=phone,
                status="pending"
            ).order_by("-created_at").first()
            if last_code and last_code.telegram_user_id:
                # Есть код, сохраняем его ID в сессию
                request.session["phone_auth_code_id"] = last_code.id
                code_id = last_code.id
            else:
                # Нет активного кода, редиректим на ввод telegram_id
                from django.urls import reverse
                return redirect(reverse("phone_enter_telegram_id"))
        except Exception as e:
            logger.error(f"Ошибка при поиске кода: {e}")
            request.session.flush()
            from django.urls import reverse
            return redirect(reverse("phone_login"))
    
    error_message = None
    
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        
        if not code:
            error_message = "Пожалуйста, введите код подтверждения"
        elif len(code) != 6 or not code.isdigit():
            error_message = "Код должен состоять из 6 цифр"
        else:
            # Проверяем код
            auth_code = PhoneAuthCode.get_valid_code(phone, code)
            
            if not auth_code:
                # Увеличиваем счетчик попыток для последнего кода
                try:
                    last_code = PhoneAuthCode.objects.filter(
                        phone=phone,
                        status="pending"
                    ).order_by("-created_at").first()
                    if last_code:
                        last_code.increment_attempts()
                        if last_code.is_max_attempts_reached():
                            error_message = (
                                "Превышено количество попыток. "
                                "Запросите новый код."
                            )
                            request.session.pop("phone_auth_phone", None)
                            request.session.pop("phone_auth_code_id", None)
                        else:
                            error_message = f"Неверный код. Осталось попыток: {last_code.max_attempts - last_code.attempts}"
                    else:
                        error_message = "Код не найден или истек. Запросите новый код."
                except Exception as e:
                    logger.error(f"Ошибка при проверке кода: {e}")
                    error_message = "Ошибка при проверке кода. Попробуйте еще раз."
            else:
                # Код верный, авторизуем пользователя
                auth_code.mark_verified(auth_code.telegram_user_id)
                
                # Сохраняем telegram_id в сессии
                request.session["telegram_id"] = int(auth_code.telegram_user_id)
                
                # Очищаем временные данные сессии
                request.session.pop("phone_auth_phone", None)
                request.session.pop("phone_auth_code_id", None)
                
                # Создаем или получаем пользователя Django и логиним
                user, _ = User.objects.get_or_create(
                    username=f"tg_{auth_code.telegram_user_id}"
                )
                
                # Сохраняем номер телефона в профиле пользователя, если есть поле
                if hasattr(user, 'phone'):
                    user.phone = phone
                    user.save()
                
                logger.info(f"Пользователь авторизован: username={user.username}, phone={phone}")
                django_login(request, user)
                return redirect("main_menu")
    
    # Получаем информацию о последнем коде для отображения
    try:
        last_code = PhoneAuthCode.objects.filter(
            phone=phone,
            status="pending"
        ).order_by("-created_at").first()
        
        attempts_left = None
        if last_code:
            attempts_left = last_code.max_attempts - last_code.attempts
    except Exception:
        attempts_left = None
    
    return render(
        request,
        "auth/phone_verify_code.html",
        {
            "phone": phone,
            "error_message": error_message,
            "attempts_left": attempts_left,
        },
    )


@require_http_methods(["POST"])
def resend_code(request):
    """
    Повторная отправка кода подтверждения
    """
    if request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Уже авторизован"})
    
    phone = request.session.get("phone_auth_phone")
    
    if not phone:
        return JsonResponse({"status": "error", "message": "Номер телефона не найден"})
    
    # Получаем telegram_user_id из последнего кода
    try:
        last_code = PhoneAuthCode.objects.filter(
            phone=phone,
            status="pending"
        ).order_by("-created_at").first()
        
        if not last_code or not last_code.telegram_user_id:
            return JsonResponse({
                "status": "error",
                "message": "Не найден активный код. Пожалуйста, начните процесс авторизации заново."
            })
        
        telegram_user_id = last_code.telegram_user_id
    except Exception as e:
        logger.error(f"Ошибка при получении telegram_user_id: {e}")
        return JsonResponse({"status": "error", "message": "Ошибка при получении данных"})
    
    # Создаем новый код
    auth_code = PhoneAuthCode.create_code(phone)
    auth_code.telegram_user_id = telegram_user_id
    auth_code.save()
    
    # Отправляем код через Telegram бота
    success = send_code_to_user(phone, auth_code.code, telegram_user_id)
    
    if success:
        request.session["phone_auth_code_id"] = auth_code.id
        return JsonResponse({
            "status": "success",
            "message": "Код отправлен повторно"
        })
    else:
        return JsonResponse({
            "status": "error",
            "message": "Не удалось отправить код"
        })
