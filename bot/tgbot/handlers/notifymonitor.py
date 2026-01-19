import sqlite3
import time
from datetime import datetime
import requests
from pathlib import Path
path = str(Path(__file__).parents[2])
token = '5519929200:AAFxf2y-QW7i3aW4hixhffFg1X7vDRG0zOQ'


users_db_path = f'{path}/tgbot/databases/data.db'

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
    while True:
        connection = sqlite3.connect(users_db_path)
        cur = connection.cursor()
        data = cur.execute('SELECT * FROM users WHERE end_pay != 0').fetchall()
        connection.close()
        current_datetime = datetime.now()
        day = current_datetime.day
        if day == 28 or day == 30:
            for i in data:
                user_id = i[0]
                logrs = requests.get(f'https://api.telegram.org/bot{token}/sendMessage?chat_id={user_id}&text=<b>Не забудьте оплатить подписку до 1-го числа!</b>&parse_mode=HTML')
            connection.close()
        time.sleep(86400)
        
time.sleep(36000)
newMonitoring()
