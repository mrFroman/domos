import time
import httpx
import json
import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional

import uvicorn
from fastapi import FastAPI, Form, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from bot.tgbot.handlers.payment_irbis import (
    genPaymentYookassa_Irbis,
    checkPaymentYookassa,
    check_type_keyboard,
)
from bot.tgbot.databases.pay_db import sendLogToUser
from config import (
    ADVERT_TOKENS_DB_PATH,
    ADVERT_POSITIONS_FILE,
    BASE_DIR,
    CONTRACT_TOKENS_DB_PATH,
    MAIN_DB_PATH,
    DB_TYPE,
    logger_api,
)

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

TEMPLATES_DIR = os.path.join(BASE_DIR, "api", "templates")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = FastAPI()
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Подключаем общее SessionMiddleware:
app.add_middleware(
    SessionMiddleware,
    secret_key="SAME_RANDOM_LONG_SECRET_KEY",
    session_cookie="session_id",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешенные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PassportData(BaseModel):
    token: str
    user_id: int
    doc_type: int
    # Риелтор
    rieltor_last_name: Optional[str]
    rieltor_first_name: Optional[str]
    rieltor_middle_name: Optional[str]
    rieltor_birth_date: Optional[str]
    rieltor_passport_series: Optional[str]
    rieltor_passport_number: Optional[str]
    rieltor_issued_by: Optional[str]
    rieltor_issue_date: Optional[str]
    rieltor_registration_address: Optional[str]
    # Клиент
    client_last_name: Optional[str]
    client_first_name: Optional[str]
    client_middle_name: Optional[str]
    client_birth_date: Optional[str]
    client_passport_series: Optional[str]
    client_passport_number: Optional[str]
    client_issued_by: Optional[str]
    client_issue_date: Optional[str]
    client_registration_address: Optional[str]


class ReportLinkRequest(BaseModel):
    user_id: int
    uuid: str
    message_id: int


class CustomStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)

        # Логируем запрошенный путь и MIME-тип
        logger_api.info(
            f"Requested path: {path}, Content-Type: {response.headers.get('Content-Type')}"
        )

        # Явно задаем MIME-типы
        mime_types = {
            ".js": "application/javascript",
            ".css": "text/css",
            ".svg": "image/svg+xml",
        }
        for ext, mime in mime_types.items():
            if path.endswith(ext):
                response.headers["Content-Type"] = mime
                break

        # Заголовки против кэширования
        response.headers.update(
            {
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )

        return response


def init_db():
    """Инициализация таблиц в БД (поддерживает SQLite и PostgreSQL)"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    # Инициализация таблицы контрактов
    db_contract = DatabaseConnection(CONTRACT_TOKENS_DB_PATH, schema="contract")
    db_contract.execute(
        """
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER,
            data_json TEXT
        )
        """
    )
    
    # Инициализация таблицы рекламы
    db_advert = DatabaseConnection(ADVERT_TOKENS_DB_PATH, schema="advert")
    db_advert.execute(
        """
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER,
            data_json TEXT,
            signal INTEGER,
            payment_status BOOLEAN DEFAULT 0,
            payment_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Добавляем колонку payment_id если её нет (только для SQLite, PostgreSQL требует отдельной миграции)
    if DB_TYPE == "sqlite":
        try:
            db_advert.execute("ALTER TABLE tokens ADD COLUMN payment_id TEXT")
        except Exception:
            pass  # Колонка уже существует


def save_passport_data1(data: dict):
    """Сохраняет данные паспорта в БД"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(CONTRACT_TOKENS_DB_PATH, schema="contract")
    # REPLACE INTO для SQLite, INSERT ... ON CONFLICT для PostgreSQL
    if DB_TYPE == "postgres":
        query = """
            INSERT INTO tokens (token, user_id, data_json) 
            VALUES (%s, %s, %s)
            ON CONFLICT (token) DO UPDATE SET 
                user_id = EXCLUDED.user_id,
                data_json = EXCLUDED.data_json
        """
    else:
        query = "REPLACE INTO tokens (token, user_id, data_json) VALUES (?, ?, ?)"
    
    db.execute(
        query,
        (
            data.get("token"),
            data.get("user_id"),
            json.dumps(data),
        ),
    )


async def load_data(token: str) -> Optional[dict]:
    """Загружает данные по токену из БД"""
    from bot.tgbot.databases.database import async_fetch_one
    
    row = await async_fetch_one(CONTRACT_TOKENS_DB_PATH, "SELECT data_json FROM tokens WHERE token = ?", (token,), schema="contract")
    if row and row.get("data_json"):
        return json.loads(row["data_json"])
    return None


@app.get("/edit/{token}", response_class=HTMLResponse)
async def edit_passport_data_page(request: Request, token: str):
    data = await load_data(token)
    if not data:
        logger_api.error(HTTPException(status_code=404, detail="Токен не найден"))
        raise HTTPException(status_code=404, detail="Токен не найден")
    logger_api.info(f"Открыли страницу изменения данных {token}")
    return templates.TemplateResponse(
        "edit_passport.html", {"request": request, **data}
    )


# @app.get("/api/secure_example", response_class=JSONResponse)
# async def secure_example(telegram_id: int = Depends(get_telegram_id)):
#     return {"ok": True, "telegram_id": telegram_id}


@app.post("/api/save_passport_data1", response_class=JSONResponse)
async def save_passport_data_api(request: Request):
    try:
        data = await request.json()
        save_passport_data1(data)
        logger_api.info(
            f"Сохраняем данные для клиента {data['user_id']}, {data['token']}"
        )
        return {"success": True}
    except Exception as e:
        logger_api.error(f"Ошибка при сохранении данных {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/send_report_link")
async def send_report_link(payload: ReportLinkRequest):
    user_id = payload.user_id
    uuid = payload.uuid
    message_id = payload.message_id
    # Ссылка на готовый отчёт
    report_url = f"https://neurochief.online/ru/base/-/services/report/v2/{uuid}/"
    # Текст и кнопка
    text = "Ваша проверка готова:"
    keyboard = {
        "inline_keyboard": [[{"text": "Посмотреть проверку", "url": report_url}]]
    }
    # Edit существующего сообщения
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    data = {
        "chat_id": user_id,
        "message_id": message_id,
        "text": text,
        "reply_markup": json.dumps(keyboard),
    }
    r = requests.post(url, data=data)
    return {"ok": True, "tg_response": r.text}


@app.get("/people_check", response_class=HTMLResponse)
async def people_check_form(request: Request, user_id: str, message_id: str):
    return templates.TemplateResponse(
        "people_check.html",
        {"request": request, "user_id": user_id, "message_id": message_id},
    )


@app.post("/people_check_submit")
async def people_check_submit(
    user_id: str = Form(...),
    message_id: str = Form(...),
    last_name: str = Form(...),
    first_name: str = Form(...),
    second_name: str = Form(""),
    birth_date: str = Form(""),
    regions: str = Form(...),
    passport_series: str = Form(""),
    passport_number: str = Form(""),
    inn: str = Form(""),
):
    token = "b2b12c33f82e0ce11134d8081478342a"
    params = {
        "token": token,
        "PeopleQuery.LastName": last_name,
        "PeopleQuery.FirstName": first_name,
        "PeopleQuery.SecondName": second_name,
        "PeopleQuery.BirthDate": birth_date,
        "regions": regions,
        "PeopleQuery.PassportSeries": passport_series,
        "PeopleQuery.PassportNumber": passport_number,
        "PeopleQuery.INN": inn,
    }
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://irbis.plus/ru/base/-/services/people-check.json", params=params
        )
        data = r.json()
        uid = data.get("uuid", None)
        if not uid:
            return HTMLResponse(
                "<b>Ошибка при получении данных. Проверьте корректность ввода и повторите попытку.</b>",
                status_code=400,
            )

        # --- Вот этот блок! ---
        # После получения uid, делаем запрос на свой API для оповещения Telegram
        # (user_id и message_id надо получать из формы!)
        report_notify_url = "https://neurochief.pro/api/send_report_link"
        notify_payload = {
            "user_id": int(user_id),
            "uuid": uid,
            "message_id": int(message_id),
        }
        try:
            notify_resp = await client.post(
                report_notify_url, json=notify_payload, timeout=10
            )
            logger_api.info("Notify Telegram:", notify_resp.text)
        except Exception as e:
            logger_api.error(f"Ошибка отправки в Telegram: {e}")
        # --- end block ---

    # Редирект на итоговую страницу IRBIS:
    redirect_url = f"https://neurochief.online/ru/base/-/services/report/v2/{uid}/"
    return RedirectResponse(redirect_url, status_code=302)


@app.get("/org_check", response_class=HTMLResponse)
async def org_check_form(request: Request, user_id: str, message_id: str):
    return templates.TemplateResponse(
        "org_check.html",
        {"request": request, "user_id": user_id, "message_id": message_id},
    )


@app.post("/org_check_submit")
async def org_check_submit(
    user_id: str = Form(...),
    message_id: str = Form(...),
    inn: str = Form(...),
    ogrn: str = Form(...),
):
    token = "b2b12c33f82e0ce11134d8081478342a"
    params = {"token": token, "inn": inn, "ogrn": ogrn}
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://irbis.plus/ru/base/-/services/org-check.json", params=params
        )
        data = r.json()
        uid = data.get("uuid", None)
        if not uid:
            return HTMLResponse(
                "<b>Ошибка при получении данных. Проверьте корректность ввода и повторите попытку.</b>",
                status_code=400,
            )
        report_notify_url = "https://neurochief.pro/api/send_report_link"
        notify_payload = {
            "user_id": int(user_id),
            "uuid": uid,
            "message_id": int(message_id),
        }
        try:
            notify_resp = await client.post(
                report_notify_url, json=notify_payload, timeout=10
            )
            logger_api.info("Notify Telegram:", notify_resp.text)
        except Exception as e:
            logger_api.error(f"Ошибка отправки в Telegram: {e}")
    # Редирект на итоговую страницу IRBIS:
    redirect_url = f"https://neurochief.online/ru/base/-/services/report/v2/{uid}/"
    return RedirectResponse(redirect_url, status_code=302)


@app.get("/house_check", response_class=HTMLResponse)
async def house_check_form(request: Request, user_id: str, message_id: str):
    return templates.TemplateResponse(
        "house_check.html",
        {"request": request, "user_id": user_id, "message_id": message_id},
    )


@app.post("/house_check_submit")
async def house_check_submit(
    user_id: str = Form(...), message_id: str = Form(...), egrn: str = Form(...)
):
    token = "b2b12c33f82e0ce11134d8081478342a"
    params = {"token": token, "EgrnQuery.CadNum": egrn}
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://irbis.plus/ru/base/-/services/egrn-check.json", params=params
        )
        data = r.json()
        uid = data.get("uuid", None)
        if not uid:
            return HTMLResponse(
                "<b>Ошибка при получении данных. Проверьте корректность ввода и повторите попытку.</b>",
                status_code=400,
            )
        report_notify_url = "https://neurochief.pro/api/send_report_link"
        notify_payload = {
            "user_id": int(user_id),
            "uuid": uid,
            "message_id": int(message_id),
        }
        try:
            notify_resp = await client.post(
                report_notify_url, json=notify_payload, timeout=10
            )
            logger_api.info("Notify Telegram:", notify_resp.text)
        except Exception as e:
            logger_api.error(f"Ошибка отправки в Telegram: {e}")
    # Редирект на итоговую страницу IRBIS:
    redirect_url = f"https://neurochief.online/ru/base/-/services/report/v2/{uid}/"
    return RedirectResponse(redirect_url, status_code=302)


@app.post("/api/save_advert_data", response_class=JSONResponse)
async def save_advert_data_api(request: Request):
    """Сохраняет данные заявки на рекламу"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    try:
        data = await request.json()
        
        db = DatabaseConnection(ADVERT_TOKENS_DB_PATH, schema="advert")
        
        # REPLACE INTO для SQLite, INSERT ... ON CONFLICT для PostgreSQL
        if DB_TYPE == "postgres":
            query = """
                INSERT INTO tokens (token, user_id, data_json, signal, payment_status)
                VALUES (%s, %s, %s, %s, FALSE)
                ON CONFLICT (token) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    data_json = EXCLUDED.data_json,
                    signal = EXCLUDED.signal
            """
        else:
            query = """
                REPLACE INTO tokens (token, user_id, data_json, signal, payment_status)
                VALUES (?, ?, ?, ?, 0)
            """
        
        signal = data.get("signal")

        if DB_TYPE == "postgres":
            signal = bool(signal) if signal is not None else None

        db.execute(
            query,
            (
                data.get("token"),
                data.get("user_id"),
                json.dumps(data),
                signal
            ),
        )

        logger_api.info(
            f"Сохранили данные для клиента {data['user_id']}, {data['token']}"
        )
        return {"success": True}
    except Exception as e:
        logger_api.error(f"Ошибка при сохранении данных {e}")
        return {"success": False, "error": str(e)}


async def load_advert_data(token):
    """Загружает данные рекламы по токену из БД"""
    from bot.tgbot.databases.database import async_fetch_one
    
    row = await async_fetch_one(ADVERT_TOKENS_DB_PATH, "SELECT data_json FROM tokens WHERE token = ?", (token,), schema="advert")
    if row and row.get("data_json"):
        return json.loads(row["data_json"])
    return None


@app.get("/api/advert_positions", response_class=JSONResponse)
async def get_advert_positions():
    """Получение списка позиций рекламы"""
    try:
        with open(ADVERT_POSITIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {"success": True, "positions": data.get("positions", [])}
    except FileNotFoundError:
        logger_api.error("Файл позиций рекламы не найден")
        return {"success": False, "error": "Файл позиций не найден"}
    except Exception as e:
        logger_api.error(f"Ошибка при загрузке позиций рекламы: {e}")
        return {"success": False, "error": "Ошибка загрузки позиций"}


@app.get("/api/send_advert_form/{token}", response_class=HTMLResponse)
async def send_advert_form(request: Request, token: str):
    data = await load_advert_data(token)
    if not data:
        logger_api.error("Токен: {token} не найден")
        raise HTTPException(status_code=404, detail="Токен не найден")
    logger_api.info(f"Открыли заявки на рекламу по токену: {token}")

    # Загружаем позиции рекламы
    try:
        with open(ADVERT_POSITIONS_FILE, "r", encoding="utf-8") as f:
            positions_data = json.load(f)
            positions = positions_data.get("positions", [])
    except Exception as e:
        logger_api.error(f"Ошибка при загрузке позиций для формы: {e}")
        positions = []

    return templates.TemplateResponse(
        "advert.html",
        {"request": request, **data, "positions": positions},
    )


def wait_advert_payment_signal(user_id, payment_id):
    """Устаревшая функция - теперь используется webhook"""
    # Эта функция больше не используется, так как мы перешли на webhook
    # Оставлена для обратной совместимости, но не вызывается
    from bot.tgbot.databases.database import DatabaseConnection
    
    while True:
        status = checkPaymentYookassa(payment_id)
        if status == "succeeded":
            db = DatabaseConnection(ADVERT_TOKENS_DB_PATH, schema="advert")
            db.execute(
                "UPDATE tokens SET payment_status = %s WHERE user_id = %s",
                (1, user_id),
            )
            logger_api.info(
                f"✅ Оплата платежа: {payment_id} для пользователя {user_id} прошла успешно!"
            )
            sendLogToUser(
                text="✅ Оплата заявки на рекламу прошла успешно!",
                user_id=user_id,
            )
            return
        elif status == "canceled":
            db = DatabaseConnection(ADVERT_TOKENS_DB_PATH, schema="advert")
            db.execute(
                "UPDATE tokens SET payment_status = %s WHERE user_id = %s",
                (0, user_id),
            )
            logger_api.error(
                f"❌ Оплата платежа: {payment_id} для пользователя {user_id} отменена."
            )
            sendLogToUser(
                text="❌ Оплата заявки на рекламу отменена!",
                user_id=user_id,
            )
            return
        else:
            logger_api.warning(
                f"Оплата платежа: {payment_id} для пользователя {user_id} ещё не прошла."
            )
        time.sleep(10)


@app.post("/api/create_advert_payment")
async def create_payment(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    user_id = str(data.get("user_id", ""))
    token = data.get("token")  # Получаем token из запроса
    
    # Для пользователя 779889025 всегда цена 1 рубль
    if user_id == "779889025" or user_id == 779889025:
        price = "1.00"
    else:
        price = str(data.get("price", 0))
        price = "".join([price, ".00"])

    try:
        # Создаем платеж
        payment_id, payment_url = genPaymentYookassa_Irbis(
            price=price,
            description="Оплата рекламы",
            purpose="advert_payment",
            user_id=user_id,
        )
        
        # Сохраняем payment_id в БД для связи с конкретной заявкой (token)
        from bot.tgbot.databases.database import DatabaseConnection
        
        db_advert = DatabaseConnection(ADVERT_TOKENS_DB_PATH, schema="advert")
        
        if token:
            # Если передан token, обновляем конкретную запись
            db_advert.execute(
                "UPDATE tokens SET payment_id = %s WHERE token = %s",
                (payment_id, token),
            )
            logger_api.info(
                f"✅ Сохранен payment_id={payment_id} для token={token}, user_id={user_id}"
            )
        else:
            # Если token не передан, используем старую логику (для обратной совместимости)
            logger_api.warning(f"⚠️ Token не передан в запросе создания платежа для user_id={user_id}")
            # Находим самую последнюю неоплаченную запись
            row = db_advert.fetchone(
                "SELECT token FROM tokens WHERE user_id = %s AND payment_status = 0 ORDER BY created_at DESC LIMIT 1",
                (user_id,),
            )
            
            if row and row.get("token"):
                found_token = row["token"]
                db_advert.execute(
                    "UPDATE tokens SET payment_id = %s WHERE token = %s",
                    (payment_id, found_token),
                )
                logger_api.info(
                    f"✅ Сохранен payment_id={payment_id} для user_id={user_id}, token={found_token} (найдена последняя неоплаченная)"
                )
            else:
                logger_api.error(
                    f"❌ Не найдена неоплаченная запись для user_id={user_id} при сохранении payment_id={payment_id}"
                )
        # Убираем polling - теперь используем webhook
        # background_tasks.add_task(wait_advert_payment_signal, user_id, payment_id)
        return JSONResponse({"success": True, "payment_url": payment_url})
    except Exception as e:
        logger_api.error(f"Ошибка создания платежа: {e}")
        return JSONResponse({"success": False, "error": str(e)})


@app.post("/api/yookassa_webhook")
async def yookassa_webhook(request: Request):
    """Webhook для обработки платежей YooKassa"""
    client_ip = request.client.host if request.client else "unknown"
    logger_api.info(f"Получен POST запрос на /api/yookassa_webhook от {client_ip}")

    try:
        data = await request.json()
        logger_api.info(f"YooKassa webhook data: {data}")
    except Exception as e:
        logger_api.error(f"Ошибка парсинга JSON от YooKassa: {e}")
        return PlainTextResponse("Bad Request", status_code=400)

    # Проверяем тип события
    event_type = data.get("event")
    payment_object = data.get("object", {})

    if not event_type or not payment_object:
        logger_api.warning(f"Неполные данные от YooKassa: event={event_type}")
        return PlainTextResponse("OK", status_code=200)

    payment_id = payment_object.get("id")
    status = payment_object.get("status")
    metadata = payment_object.get("metadata", {})
    purpose = metadata.get("purpose", "")
    user_id = metadata.get("user_id")

    logger_api.info(
        f"YooKassa webhook: event={event_type}, payment_id={payment_id}, "
        f"status={status}, purpose={purpose}, user_id={user_id}"
    )

    # Обрабатываем разные типы событий
    if event_type == "payment.succeeded":
        if purpose == "advert_payment":
            # Обработка успешной оплаты рекламы
            # Обновляем по payment_id, а не по user_id, так как у пользователя может быть несколько заявок
            try:
                from bot.tgbot.databases.database import DatabaseConnection
                
                db_advert = DatabaseConnection(ADVERT_TOKENS_DB_PATH, schema="advert")
                
                # Сначала пытаемся обновить по payment_id (более точно)
                db_advert.execute(
                    "UPDATE tokens SET payment_status = %s WHERE payment_id = %s",
                    (1, payment_id),
                )
                
                # Проверяем, обновилось ли что-то (для PostgreSQL нужно проверить через SELECT)
                # Для обратной совместимости, если не нашли по payment_id, пробуем по user_id
                if user_id:
                    # Пробуем обновить по user_id для обратной совместимости
                    db_advert.execute(
                        "UPDATE tokens SET payment_status = %s, payment_id = %s WHERE user_id = %s AND payment_status = 0",
                        (1, payment_id, user_id),
                    )
                
                logger_api.info(
                    f"✅ Оплата рекламы прошла успешно! payment_id={payment_id}, user_id={user_id}"
                )
                if user_id:
                    sendLogToUser(
                        text="✅ Оплата заявки на рекламу прошла успешно!",
                        user_id=user_id,
                    )
            except Exception as e:
                logger_api.error(f"Ошибка при обновлении статуса оплаты рекламы: {e}")

        elif purpose == "irbis_check":
            # Обработка успешной оплаты проверки IRBIS
            from bot.tgbot.databases.database import DatabaseConnection
            
            # Если user_id нет в metadata, пытаемся найти его в БД
            if not user_id:
                try:
                    db_main = DatabaseConnection(MAIN_DB_PATH, schema="main")
                    row = db_main.fetchone(
                        "SELECT user_id FROM payments WHERE payment_id = %s",
                        (payment_id,),
                    )
                    if row and row.get("user_id"):
                        user_id = str(row["user_id"])
                except Exception as e:
                    logger_api.error(f"Ошибка при поиске user_id по payment_id: {e}")
            
            if user_id:
                try:
                    # Обновляем статус платежа в основной БД
                    db_main = DatabaseConnection(MAIN_DB_PATH, schema="main")
                    db_main.execute(
                        "UPDATE payments SET status = 1 WHERE payment_id = %s",
                        (payment_id,),
                    )
                    logger_api.info(
                        f"✅ Оплата IRBIS прошла успешно! payment_id={payment_id}, user_id={user_id}"
                    )
                    # Отправляем первое сообщение
                    sendLogToUser(
                        text="✅ Оплата прошла успешно! Доступ к IRBIS открыт.",
                        user_id=user_id,
                    )
                    # Отправляем второе сообщение с клавиатурой
                    # Создаем клавиатуру для выбора типа проверки
                    keyboard_markup = {
                        "inline_keyboard": [
                            [{"text": "🏢 Юр. лицо", "callback_data": "check_jur"}],
                            [{"text": "👤 Физ. лицо", "callback_data": "check_fiz"}],
                            [{"text": "🏠 Недвижимость", "callback_data": "check_realty"}],
                        ]
                    }
                    keyboard_json = json.dumps(keyboard_markup)
                    requests.get(
                        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
                        params={
                            'chat_id': user_id,
                            'text': 'Выберите, кого вы хотите проверить:',
                            'reply_markup': keyboard_json,
                        }
                    )
                except Exception as e:
                    logger_api.error(f"Ошибка при обновлении статуса оплаты IRBIS: {e}")

    elif event_type == "payment.canceled":
        if purpose == "advert_payment":
            # Обработка отмены оплаты рекламы
            from bot.tgbot.databases.database import DatabaseConnection
            
            try:
                db_advert = DatabaseConnection(ADVERT_TOKENS_DB_PATH, schema="advert")
                token = metadata.get("token")
                
                # Обновляем по payment_id
                db_advert.execute(
                    "UPDATE tokens SET payment_status = %s WHERE payment_id = %s",
                    (0, payment_id),
                )
                
                # Если не нашли по payment_id и есть token, пробуем по token
                if token:
                    db_advert.execute(
                        "UPDATE tokens SET payment_status = %s WHERE token = %s",
                        (0, token),
                    )
                
                logger_api.error(
                    f"❌ Оплата рекламы отменена. payment_id={payment_id}, user_id={user_id}, token={token}"
                )
                if user_id:
                    sendLogToUser(
                        text="❌ Оплата заявки на рекламу отменена!",
                        user_id=user_id,
                    )
            except Exception as e:
                logger_api.error(f"Ошибка при обновлении статуса отмены рекламы: {e}")

        elif purpose == "irbis_check":
            # Обработка отмены оплаты IRBIS
            if user_id:
                logger_api.error(
                    f"❌ Оплата IRBIS отменена. payment_id={payment_id}, user_id={user_id}"
                )
                sendLogToUser(
                    text="❌ Оплата проверки IRBIS отменена!",
                    user_id=user_id,
                )

    elif event_type == "payment.waiting_for_capture":
        logger_api.info(f"Платеж ожидает подтверждения: payment_id={payment_id}")

    elif event_type == "refund.succeeded":
        logger_api.info(f"Возврат успешно выполнен: payment_id={payment_id}")

    # Всегда возвращаем 200 OK для YooKassa
    return PlainTextResponse("OK", status_code=200)


@app.post("/tinkoff_payment_webhook/")
async def tinkoff_webhook(
    request: Request,
):
    """Webhook для обработки платежей Tinkoff"""
    client_ip = request.client.host if request.client else "unknown"
    logger_api.info(f"Получен POST запрос на /tinkoff_payment_webhook/ от {client_ip}")

    try:
        data = await request.json()
    except Exception:
        form = await request.form()
        data = dict(form)
    logger_api.info(f"{data=}")


def mark_payment_failed(payment_id, reason):
    """Отмечает платеж как неудачный"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        """
        UPDATE rec_payments
        SET status = 'failed',
            fail_reason = %s,
            updated_at = %s
        WHERE payment_id_last = %s OR id = %s
        """,
        (reason, now, payment_id, payment_id),
    )


def calculate_next_payment_date(now: datetime) -> str:
    """
    Возвращает ISO дату следующего платежа:
    - до 15 числа → конец текущего месяца
    - с 15 числа → конец следующего месяца
    """
    if now.day < 15:
        # конец текущего месяца
        first_next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        end_date = first_next_month - timedelta(days=1)
    else:
        # конец следующего месяца
        first_next_next_month = (now.replace(day=1) + timedelta(days=64)).replace(day=1)
        end_date = first_next_next_month - timedelta(days=1)

    return end_date.replace(
        hour=now.hour,
        minute=now.minute,
        second=now.second,
        microsecond=0
    ).isoformat()



def parse_to_unix(dt_str: str) -> int:
    """
    Преобразует ISO-дату с таймзоной и без в unix timestamp
    """
    try:
        # вариант с таймзоной
        dt = datetime.fromisoformat(dt_str)
    except ValueError:
        # fallback (на всякий)
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return int(dt.timestamp())


@app.post("/api/tinkoff_recurrent_payment_webhook/")
async def tinkoff_recurrent_payment_webhook(request: Request):
    """Webhook для обработки рекуррентных платежей Tinkoff"""
    client_ip = request.client.host if request.client else "unknown"
    logger_api.info(f"Webhook from {client_ip}")

    # --- Чтение данных ---
    try:
        data = await request.json()
    except Exception:
        data = dict(await request.form())

    logger_api.info(f"Webhook data: {data}")

    # --- Базовая валидация ---
    payment_id = data.get("PaymentId")
    rebill_id = data.get("RebillId")
    status = data.get("Status")
    success = data.get("Success")

    if not payment_id:
        return JSONResponse(
            {"success": False, "error": "PaymentId not provided"},
        )

    # --- Проверяем статус платежа ---
    if str(success).lower() != "true" and status not in ("CONFIRMED", "AUTHORIZED"):
        logger_api.warning(f"Payment {payment_id} failed with status {status}")
        await mark_payment_failed(payment_id, status)
        return JSONResponse({"success": True})

    # --- Дата начала списания ---
    start_dt = datetime.utcnow().replace(microsecond=0).isoformat()

    # --- Следующий платеж через 30 дней ---
    now_utc = datetime.utcnow().replace(microsecond=0)
    next_dt = calculate_next_payment_date(now_utc)

    # --- Обновление в БД ---
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main")

    # Проверяем существование платежа
    # row = db.fetchone(
    #     "SELECT * FROM rec_payments WHERE payment_id_last = %s OR id = %s",
    #     (str(payment_id), str(payment_id)),
    # )

    row = db.fetchone(
        "SELECT * FROM rec_payments WHERE payment_id_last = %s",
        (str(payment_id),),
    )

    if not row:
        logger_api.error(f"No payment record for PaymentId {payment_id}")
        return JSONResponse({"success": False, "error": "Payment not found"})

    payment_db_id = row.get("id") or row[0] if isinstance(row, (list, tuple)) else row.get("id")
    user_id = row.get("user_id") or row[1] if isinstance(row, (list, tuple)) else row.get("user_id")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Обновляем поля
    db.execute(
        """
        UPDATE rec_payments
        SET payment_id_last = %s,
            rebill_id = COALESCE(%s, rebill_id),
            start_pay_date = %s,
            end_pay_date = %s,
            status = 'active',
            updated_at = %s
        WHERE id = %s
        """,
        (str(payment_id), rebill_id, start_dt, next_dt, now, payment_db_id),
    )

    # обновляем в таблице пользователей статус на 1 
    last_pay_unix = parse_to_unix(start_dt)
    end_pay_unix = parse_to_unix(next_dt)
    db.execute(
        """
        UPDATE users
        SET pay_status = 1,
            last_pay = %s,
            end_pay = %s
        WHERE user_id = %s
        """,
        (
            last_pay_unix,
            end_pay_unix,
            str(user_id),
        ),
    )

    sendLogToUser(
        text=f"✅ Подписка на DomosClub активирована! Следующее списание: {next_dt}",
        user_id=user_id,
    )
    logger_api.info(
        f"Recurrent update for {payment_id}: rebill={rebill_id}, "
        f"start={start_dt}, end={next_dt}"
    )
    return PlainTextResponse("OK", status_code=200)
    # return JSONResponse({"success": True})


if __name__ == "__main__":
    init_db()
    # TODO Вернуть после тестов
    uvicorn.run(app, host="0.0.0.0", port=8001)
    # uvicorn.run(app, host="localhost", port=8001)
