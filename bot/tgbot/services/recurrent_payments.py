import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from bot.tgbot.databases.pay_db import sendLogToUser
from bot.tgbot.databases.database import AsyncDatabaseConnection, DB_TYPE
from bot.tgbot.handlers.tinkoff_api import TinkoffPayment
from config import MAIN_DB_PATH, logger_bot


async def get_due_recurrents():
    """Получает рекуррентные платежи, которые нужно обработать"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    db = AsyncDatabaseConnection(MAIN_DB_PATH, schema="main")
    
    if DB_TYPE == "postgres":
        query = """
            SELECT *
            FROM rec_payments
            WHERE is_recurrent = 1
            AND status = 'active'
            AND rebill_id IS NOT NULL
            AND end_pay_date <= %s
        """
        rows = await db.fetchall(query, (now,))
    else:
        query = """
            SELECT *
            FROM rec_payments
            WHERE is_recurrent = 1
            AND status = 'active'
            AND rebill_id IS NOT NULL
            AND datetime(replace(end_pay_date, 'T', ' ')) <= datetime(%s)
        """
        rows = await db.fetchall(query, (now,))
    
    return rows if rows else []


async def get_expired_pending_payments():
    """Получает просроченные pending платежи"""
    db = AsyncDatabaseConnection(MAIN_DB_PATH, schema="main")
    
    if DB_TYPE == "postgres":
        query = """
            SELECT *
            FROM rec_payments
            WHERE status = 'pending'
              AND created_at <= NOW() - INTERVAL '3 days'
        """
    else:
        query = """
            SELECT *
            FROM rec_payments
            WHERE status = 'pending'
              AND created_at <= datetime('now', '-3 days')
        """
    
    rows = await db.fetchall(query)
    return rows if rows else []


async def init_repeat(payment):
    order_id = f"rec-{payment['id']}-{uuid.uuid4()}"
    description = "Повтор рекуррентной подписки"

    res = TinkoffPayment.init_repeat_recurrent_payment(
        order_id=order_id,
        description=description,
    )

    if not res.get("Success"):
        logger_bot.error(
            f"Не удалось инициализировать платёж с payment_id: {payment}",
        )
        raise RuntimeError(f"Init repeat failed: {res}")
    logger_bot.info(f"Инициализирован новый платёж: {res}")

    return res["PaymentId"]


async def charge(payment_id, rebill_id):
    res = TinkoffPayment.charge_recurrent_payment(
        payment_id=str(payment_id),
        rebill_id=str(rebill_id),
    )

    if not res.get("Success"):
        logger_bot.error(
            f"Не удалось оплатить платёж с payment_id: {payment_id}, rebill_id: {rebill_id}",
        )
        raise RuntimeError(f"Charge failed: {res}")
    logger_bot.info(f"Оплачен платёж: {res}")

    return res


async def update_payment_dates(payment):
    """Обновляет даты платежа и подписки пользователя"""
    new_start = datetime.now(timezone.utc)
    new_end = new_start + timedelta(days=30)
    
    start_ts = int(new_start.timestamp())
    end_ts = int(new_end.timestamp())

    db = AsyncDatabaseConnection(MAIN_DB_PATH, schema="main")
    
    # 1. Получаем user_id по payment.id
    payment_row = await db.fetchone("SELECT user_id FROM rec_payments WHERE id = %s", (payment["id"],))
    
    if not payment_row:
        raise ValueError(f"Платёж с id={payment['id']} не найден")
    
    if isinstance(payment_row, dict):
        user_id = payment_row.get('user_id')
    else:
        user_id = payment_row[0] if payment_row else None
    
    if not user_id:
        raise ValueError(f"Не найден user_id для платежа id={payment['id']}")

    # 2. Обновляем rec_payments
    if DB_TYPE == "postgres":
        await db.execute(
            """
            UPDATE rec_payments
            SET start_pay_date = %s,
                end_pay_date = %s,
                updated_at = NOW(),
                retry_count = 0
            WHERE id = %s
            """,
            (new_start.isoformat(), new_end.isoformat(), payment["id"]),
        )
    else:
        await db.execute(
            """
            UPDATE rec_payments
            SET start_pay_date = %s,
                end_pay_date = %s,
                updated_at = datetime('now'),
                retry_count = 0
            WHERE id = %s
            """,
            (new_start.isoformat(), new_end.isoformat(), payment["id"]),
        )

    # 3. Обновляем users
    await db.execute(
        """
        UPDATE users
        SET pay_status = 1,
            last_pay = %s,
            end_pay = %s
        WHERE user_id = %s
        """,
        (start_ts, end_ts, user_id),
    )

    logger_bot.info(
        f"Подписка обновлена: payment_id={payment['id']}, user_id={user_id}"
    )

    # async with aiosqlite.connect(MAIN_DB_PATH) as db:
    #     await db.execute(
    #         """
    #         UPDATE rec_payments
    #         SET start_pay_date = ?,
    #             end_pay_date = ?,
    #             updated_at = datetime('now'),
    #             retry_count = 0
    #         WHERE id = ?
    #     """,
    #         (
    #             new_start.isoformat(),
    #             new_end.isoformat(),
    #             payment["id"],
    #         ),
    #     )



    #     await db.commit()
    # logger_bot.info(f"Установлены новые даты для платежа с payment_id: {payment}")


async def delete_payment(payment):
    """Удаляет просроченный pending платеж"""
    db = AsyncDatabaseConnection(MAIN_DB_PATH, schema="main")
    await db.execute("DELETE FROM rec_payments WHERE id = %s", (payment["id"],))
    logger_bot.info(f"Удалён pending-платёж старше 3 дней: id={payment['id']}")


async def mark_failed(payment, reason):
    """Отмечает платеж как неудачный"""
    db = AsyncDatabaseConnection(MAIN_DB_PATH, schema="main")
    
    if DB_TYPE == "postgres":
        await db.execute(
            """
            UPDATE rec_payments
            SET status = 'failed',
                fail_reason = %s,
                retry_count = retry_count + 1,
                updated_at = NOW()
            WHERE id = %s
        """,
            (reason, payment["id"]),
        )
    else:
        await db.execute(
            """
            UPDATE rec_payments
            SET status = 'failed',
                fail_reason = %s,
                retry_count = retry_count + 1,
                updated_at = datetime('now')
            WHERE id = %s
        """,
            (reason, payment["id"]),
        )


async def process_recurrents():
    await process_expired_pending()

    payments = await get_due_recurrents()
    logger_bot.info(f"Получен список платежей на оплату: {payments}")

    for payment in payments:
        try:
            # Init повторного платежа
            payment_id = await init_repeat(payment)

            # Charge платежа
            await charge(payment_id, payment["rebill_id"])

            # Успех — обновляем даты
            await update_payment_dates(payment)

        except Exception as e:
            await mark_failed(payment, str(e))
        sendLogToUser(
            text="✅ Подписка на DomosClub продлена!",
            user_id=payment["user_id"],
        )


async def process_expired_pending():
    payments = await get_expired_pending_payments()

    if payments:
        logger_bot.info(f"Найдено pending-платежей на удаление: {len(payments)}")

    for payment in payments:
        try:
            await delete_payment(payment)
        except Exception as e:
            logger_bot.error(
                f"Ошибка при удалении pending-платежа {payment['id']}: {e}"
            )


async def recurrent_worker():
    while True:
        try:
            await process_recurrents()
        except Exception as e:
            print(f"Ошибка в recurrent worker: {e}")

        await asyncio.sleep(60 * 60)


async def main():
    # recurrent_worker()
    await recurrent_worker()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Recurrent worker stopped manually.")
