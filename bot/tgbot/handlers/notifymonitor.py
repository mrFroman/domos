import time
from datetime import datetime
import requests

from bot.tgbot.databases.database import DatabaseConnection
from config import MAIN_DB_PATH

token = '5519929200:AAFxf2y-QW7i3aW4hixhffFg1X7vDRG0zOQ'

# def monitorTime():
#     while True:
#         connection = sqlite3.connect(deps_db_path)
#         cur = connection.cursor()
#         cur.execute('UPDATE userFinance SET balance = deposit_balance +(deposit_balance/100*0.0625) WHERE deposit_balance > 0')
#         connection.commit()
#         connection.close()
#         sendLogToAdm('<i>Юзерам начислено по 0.0625%</i>')
#         time.sleep(3600)

# #monitorTime()

def newMonitoring():
    """Мониторинг уведомлений о подписке. Напоминания только тем, у кого не включён автоплатёж."""
    while True:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main")
        # Только пользователи с подпиской (end_pay != 0) и без активного автоплатежа
        data = db.fetchall("""
            SELECT u.user_id FROM users u
            LEFT JOIN rec_payments r ON r.user_id = u.user_id AND r.status = 'active'
            WHERE u.end_pay != 0 AND r.user_id IS NULL
        """)
        current_datetime = datetime.now()
        day = current_datetime.day
        if day == 28 or day == 30:
            for i in data:
                if isinstance(i, dict):
                    user_id = i.get('user_id', '')
                else:
                    user_id = i[0] if len(i) > 0 else ''
                if user_id:
                    requests.get(f'https://api.telegram.org/bot{token}/sendMessage?chat_id={user_id}&text=<b>Не забудьте оплатить подписку до 1-го числа!</b>&parse_mode=HTML')
        time.sleep(86400)
        
time.sleep(36000)
newMonitoring()
