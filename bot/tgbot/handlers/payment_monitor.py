import time
import datetime
import requests
import hashlib

from bot.tgbot.databases.database import DatabaseConnection
from config import MAIN_DB_PATH, logger_bot


# Настройки Тинькофф
TERMINAL_KEY = '1741778432520'
SECRET_KEY = "_AMRg%%S%W2eM&e9"


def sendLogToUser(text, user_id):
    requests.get(
        f'https://api.telegram.org/bot5519929200:AAFxf2y-QW7i3aW4hixhffFg1X7vDRG0zOQ/sendMessage?chat_id={user_id}&text={text}&parse_mode=HTML')


def generate_token(data):
    sorted_items = sorted(data.items())
    token_str = ''.join([str(v) for k, v in sorted_items])
    return hashlib.sha256(token_str.encode('utf-8')).hexdigest()


def checkPaymentTinkoff(payment_id):
    url = 'https://securepay.tinkoff.ru/v2/GetState'
    payload = {
        "TerminalKey": TERMINAL_KEY,
        "PaymentId": payment_id,
        "Token": generate_token({
            "TerminalKey": TERMINAL_KEY,
            "PaymentId": payment_id,
            "Password": SECRET_KEY
        })
    }
    response = requests.post(url, json=payload)
    data = response.json()
    return data.get('Status', 'UNKNOWN')


def getPayment(id):
    """Получает информацию о платеже"""
    db = DatabaseConnection(MAIN_DB_PATH, schema="main")
    info = db.fetchone("SELECT * FROM payments WHERE payment_id = %s", (id,))
    if info:
        if isinstance(info, dict):
            user_id = info.get('user_id', '')
            amount = int(info.get('amount', 0))
            created = int(info.get('created', 0))
            status = int(info.get('status', 0))
        else:
            user_id = info[0] if len(info) > 0 else ''
            amount = int(info[2]) if len(info) > 2 else 0
            created = int(info[3]) if len(info) > 3 else 0
            status = int(info[4]) if len(info) > 4 else 0
        return user_id, amount, created, status
    return '', 0, 0, 0


def makePaymentCompleted(id):
    """Отмечает платеж как завершенный и обновляет подписку"""
    user_id, amount, created, status = getPayment(id)
    db = DatabaseConnection(MAIN_DB_PATH, schema="main")
    now_ts = int(time.time())

    # Получаем текущую дату окончания подписки пользователя
    result = db.fetchone('SELECT end_pay FROM users WHERE user_id = %s', (user_id,))
    if result:
        if isinstance(result, dict):
            current_end_pay = result.get('end_pay', 0)
        else:
            current_end_pay = result[0] if result[0] else None
    else:
        current_end_pay = None

    if current_end_pay and current_end_pay > now_ts:
        # Если подписка активна — продлеваем от текущей end_pay (+срок в зависимости от суммы)
        t = datetime.datetime.fromtimestamp(current_end_pay).date()
        if amount == 10000:
            t += datetime.timedelta(days=33)
        elif amount == 12300:
            t += datetime.timedelta(days=31)
        elif amount == 30000:
            t += datetime.timedelta(days=93)
        elif amount == 60000:
            t += datetime.timedelta(days=186)
        elif amount == 120000:
            t += datetime.timedelta(days=365)
    else:
        # Если подписки нет — старая логика (срок зависит от суммы и дня оплаты)
        t = datetime.date.today()
        if amount == 10000:
            t += datetime.timedelta(days=62 if t.day >= 20 else 31)
        elif amount == 12300:
            t += datetime.timedelta(days=62 if t.day >= 17 else 31)
        elif amount == 30000:
            t += datetime.timedelta(days=124 if t.day >= 20 else 93)
        elif amount == 60000:
            t += datetime.timedelta(days=217 if t.day >= 20 else 186)
        elif amount == 120000:
            t += datetime.timedelta(days=396 if t.day >= 20 else 365)

    # Сдвигаем дату на 1-е число следующего месяца
    t = t.replace(day=1)
    timestamp2 = int(time.mktime(t.timetuple()))

    if status == 0:
        db.execute('UPDATE payments SET status = 1 WHERE payment_id = %s', (id,))
        db.execute('UPDATE users SET last_pay = %s WHERE user_id = %s', (now_ts, user_id,))
        db.execute('UPDATE users SET end_pay = %s WHERE user_id = %s', (timestamp2, user_id,))
        db.execute('UPDATE users SET pay_status = 1 WHERE user_id = %s', (user_id,))


def newMonitoring():
    """Мониторинг платежей"""
    while True:
        time.sleep(10)
        db = DatabaseConnection(MAIN_DB_PATH, schema="main")
        now_ts = int(time.time())
        data = db.fetchall('SELECT * FROM payments WHERE status = 0 ORDER BY ts DESC')
        data = data[:100]

        for i in data:
            try:
                if isinstance(i, dict):
                    user_id = i.get('user_id', '')
                    payment_id = i.get('payment_id', '')
                    created = int(i.get('created', 0))
                else:
                    user_id = i[0] if len(i) > 0 else ''
                    payment_id = i[1] if len(i) > 1 else ''
                    created = int(i[3]) if len(i) > 3 else 0
                
                result = checkPaymentTinkoff(payment_id)
                if result == 'CONFIRMED':
                    makePaymentCompleted(payment_id)
                    logger_bot.info(f"✅ Оплата прошла {payment_id}")

                    sendLogToUser(
                        '<b>✅ Успешно оплачено</b>\nНажмите - /start', user_id)
                    sendLogToUser('''<b>Территория свободы риелторов ДОМОС CLUB приветствует тебя!</b>
По подключению к нашим системам, настройкам доступов и личных кабинетов тебе поможет – Ирина Гурдуза, @Irina_Domos +79193747077 

В дальнейшей работе ты можешь обращаться за помощью к офис-менеджеру - Ольге Яковой, @yakova_olga   +79030821574

Вопросами публикации рекламы занимается - Кузнецова Ирина, @twinssirina +79826772623

По вопросам связанным с новостройками - Лане Татьяна, @TatyanaLane +79003894823

По вопросам обучений, дискуссионных клубов - Снежана Ермина, @SnegaE  +79826079907

А если тебе захотелось снять крутое видео для своих социальных сетей, то обратись с нашему контент директору - Стенякину Александру,   @Alxstndom +79126334942

Но если ты не знаешь, кому задать свой вопрос – Ким Екатерина, @kmekaterina +79122666299

Если и после этого остались вопросы - Владимир Лебедев, @lebedevvs  +79634450770

В WhatsApp у нас есть сообщество с обязательными и не обязательными чатами вступи в него по ссылке - https://chat.whatsapp.com/KkN3o30hnjaEzJSfW9bi7u

Обязательно подпишись на наши соц.сети, там публикуется анонс всех мероприятий и бекстейдж жизни нашей команды: 
https://vk.com/domosclub
https://www.instagram.com/domos.top
Наш сайт: domos.club
Телеграмм канал с эфирами обучений: https://t.me/+Cbrhm0SoPHxlNGZi''', user_id)

                elif result in ['REJECTED', 'CANCELED', 'DEADLINE_EXPIRED']:
                    # Если платёж явно не прошёл — удаляем
                    db.execute('DELETE FROM payments WHERE payment_id = %s', (payment_id,))

                    sendLogToUser(
                        '<b>❌ Оплата была отменена или отклонена</b>\nПопробуйте снова — /start', user_id)
                    logger_bot.error(
                        f"⛔ Неуспешная оплата {payment_id} — удалена")

                elif created + 1800 < now_ts:
                    # Если просто вышло время ожидания (30 минут)
                    db.execute('DELETE FROM payments WHERE payment_id = %s', (payment_id,))

                    sendLogToUser(
                        '<b>❌ Время на оплату истекло</b>\nПопробуйте снова — /start', user_id)
                    logger_bot.error(
                        f"⌛ Истекло время оплаты — {payment_id} удалена")

            except Exception as e:
                logger_bot.error(f"Ошибка при проверке платежа: {e}")


newMonitoring()
