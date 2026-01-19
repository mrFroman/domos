import sqlite3
import time
import datetime
import requests
import hashlib

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
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        "SELECT * FROM payments WHERE payment_id = ?", (id,)).fetchone()
    sqlite_connection.commit()
    sqlite_connection.close()
    user_id = info[0]
    amount = int(info[2])
    created = int(info[3])
    status = int(info[4])
    return user_id, amount, created, status


def makePaymentCompleted(id):
    user_id, amount, created, status = getPayment(id)
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    cur = sqlite_connection.cursor()
    now_ts = int(time.time())

    # Получаем текущую дату окончания подписки пользователя
    cur.execute('SELECT end_pay FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    current_end_pay = result[0] if result else None

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
        cur.execute(
            'UPDATE payments SET status = 1 WHERE payment_id = ?', (id,))
        cur.execute(
            'UPDATE users SET last_pay = ? WHERE user_id = ?', (now_ts, user_id,))
        cur.execute('UPDATE users SET end_pay = ? WHERE user_id = ?',
                    (timestamp2, user_id,))
        cur.execute(
            'UPDATE users SET pay_status = 1 WHERE user_id = ?', (user_id,))
        sqlite_connection.commit()

    sqlite_connection.close()


def newMonitoring():
    while True:
        time.sleep(10)
        connection = sqlite3.connect(MAIN_DB_PATH)
        cur = connection.cursor()
        now_ts = int(time.time())
        data = cur.execute(
            'SELECT * FROM payments WHERE status = 0 ORDER BY ts DESC').fetchall()
        data = data[:100]
        connection.close()

        for i in data:
            try:
                payment_id = i[1]
                result = checkPaymentTinkoff(payment_id)
                created = int(i[3])
                if result == 'CONFIRMED':
                    makePaymentCompleted(payment_id)
                    logger_bot.info(f"✅ Оплата прошла {payment_id}")

                    sendLogToUser(
                        '<b>✅ Успешно оплачено</b>\nНажмите - /start', i[0])
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
Телеграмм канал с эфирами обучений: https://t.me/+Cbrhm0SoPHxlNGZi''', i[0])

                elif result in ['REJECTED', 'CANCELED', 'DEADLINE_EXPIRED']:
                    # Если платёж явно не прошёл — удаляем
                    connection = sqlite3.connect(MAIN_DB_PATH)
                    cur = connection.cursor()
                    cur.execute(
                        'DELETE FROM payments WHERE payment_id = ?', (payment_id,))
                    connection.commit()
                    connection.close()

                    sendLogToUser(
                        '<b>❌ Оплата была отменена или отклонена</b>\nПопробуйте снова — /start', i[0])
                    logger_bot.error(
                        f"⛔ Неуспешная оплата {payment_id} — удалена")

                elif created + 1800 < now_ts:
                    # Если просто вышло время ожидания (30 минут)
                    connection = sqlite3.connect(MAIN_DB_PATH)
                    cur = connection.cursor()
                    cur.execute(
                        'DELETE FROM payments WHERE payment_id = ?', (payment_id,))
                    connection.commit()
                    connection.close()

                    sendLogToUser(
                        '<b>❌ Время на оплату истекло</b>\nПопробуйте снова — /start', i[0])
                    logger_bot.error(
                        f"⌛ Истекло время оплаты — {payment_id} удалена")

            except Exception as e:
                logger_bot.error(f"Ошибка при проверке платежа: {e}")


newMonitoring()
