import aiosqlite
import time
import httpx
import json
import os
import requests
import sqlite3
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
)
from bot.tgbot.databases.pay_db import sendLogToUser
from config import (
    ADVERT_TOKENS_DB_PATH,
    ADVERT_POSITIONS_FILE,
    BASE_DIR,
    CONTRACT_TOKENS_DB_PATH,
    MAIN_DB_PATH,
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
    with sqlite3.connect(CONTRACT_TOKENS_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER,
                data_json TEXT
            )
        """
        )
        conn.commit()
    with sqlite3.connect(ADVERT_TOKENS_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER,
                data_json TEXT,
                signal INTEGER,
                payment_status BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def save_passport_data1(data: dict):
    with sqlite3.connect(CONTRACT_TOKENS_DB_PATH) as conn:
        conn.execute(
            "REPLACE INTO tokens (Signal, token, user_id, data_json) VALUES (?, ?, ?, ?)",
            (
                data.get("Signal"),
                data.get("token"),
                data.get("user_id"),
                json.dumps(data),
            ),
        )
        conn.commit()


async def load_data(token: str) -> Optional[dict]:
    async with aiosqlite.connect(CONTRACT_TOKENS_DB_PATH) as conn:
        async with conn.execute(
            "SELECT data_json FROM tokens WHERE token = ?", (token,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
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
    try:
        data = await request.json()

        with sqlite3.connect(ADVERT_TOKENS_DB_PATH) as conn:
            conn.execute(
                """
                REPLACE INTO tokens (
                    token,
                    user_id,
                    data_json,
                    signal,
                    payment_status
                ) VALUES (?, ?, ?, ?, 0)
                """,
                (
                    data.get("token"),
                    data.get("user_id"),
                    json.dumps(data),
                    data.get("signal"),
                ),
            )
            conn.commit()

        logger_api.info(
            f"Сохранили данные для клиента {data['user_id']}, {data['token']}"
        )
        return {"success": True}
    except Exception as e:
        logger_api.error(f"Ошибка при сохранении данных {e}")
        return {"success": False, "error": str(e)}


async def load_advert_data(token):
    async with aiosqlite.connect(ADVERT_TOKENS_DB_PATH) as conn:
        async with conn.execute(
            "SELECT data_json FROM tokens WHERE token = ?", (token,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
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
    while True:
        status = checkPaymentYookassa(payment_id)
        if status == "succeeded":
            with sqlite3.connect(ADVERT_TOKENS_DB_PATH) as conn:
                conn.execute(
                    "UPDATE tokens SET payment_status = ? WHERE user_id = ?",
                    (1, user_id),
                )
                conn.commit()
            logger_api.info(
                f"✅ Оплата платежа: {payment_id} для пользователя {user_id} прошла успешно!"
            )
            sendLogToUser(
                text="✅ Оплата заявки на рекламу прошла успешно!",
                user_id=user_id,
            )
            return
        elif status == "canceled":
            with sqlite3.connect(ADVERT_TOKENS_DB_PATH) as conn:
                conn.execute(
                    "UPDATE tokens SET payment_status = ? WHERE user_id = ?",
                    (0, user_id),
                )
                conn.commit()
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
    price = str(data.get("price", 0))
    price = "".join([price, ".00"])

    user_id = str(data.get("user_id", ""))

    try:

        payment_id, payment_url = genPaymentYookassa_Irbis(
            price,
            description="Оплата рекламы",
        )
        background_tasks.add_task(wait_advert_payment_signal, user_id, payment_id)
        return JSONResponse({"success": True, "payment_url": payment_url})
    except Exception as e:
        logger_api.error(f"Ошибка создания платежа: {e}")
        return JSONResponse({"success": False, "error": str(e)})


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
    conn = sqlite3.connect(MAIN_DB_PATH)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        UPDATE rec_payments
        SET status = 'failed',
            fail_reason = ?,
            updated_at = ?
        WHERE payment_id_last = ? OR id = ?
        """,
        (reason, now, payment_id, payment_id),
    )

    conn.commit()
    conn.close()


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
    conn = sqlite3.connect(MAIN_DB_PATH)
    cursor = conn.cursor()

    # Проверяем существование платежа
    cursor.execute(
        "SELECT * FROM rec_payments WHERE payment_id_last = ? OR id = ?",
        (str(payment_id), str(payment_id)),
    )
    row = cursor.fetchone()

    if not row:
        logger_api.error(f"No payment record for PaymentId {payment_id}")
        conn.close()
        return JSONResponse({"success": False, "error": "Payment not found"})

    payment_db_id = row[0]
    user_id = row[1]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Обновляем поля
    cursor.execute(
        """
        UPDATE rec_payments
        SET payment_id_last = ?,
            rebill_id = COALESCE(?, rebill_id),
            start_pay_date = ?,
            end_pay_date = ?,
            status = 'active',
            updated_at = ?
        WHERE id = ?
        """,
        (str(payment_id), rebill_id, start_dt, next_dt, now, payment_db_id),
    )


    # обновляем в таблице пользователей статус на 1 

    last_pay_unix = parse_to_unix(start_dt)
    end_pay_unix = parse_to_unix(next_dt)
    cursor.execute(
        """
        UPDATE users
        SET pay_status = 1,
            last_pay = ?,
            end_pay = ?
        WHERE user_id = ?
        """,
        (
            last_pay_unix,
            end_pay_unix,
            str(user_id),
        ),
    )

    conn.commit()
    conn.close()

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
