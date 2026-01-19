import sqlite3
import time
from pathlib import Path
path = str(Path(__file__).parents[2])


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
        for i in data:
            try:
                connection = sqlite3.connect(users_db_path)
                cur = connection.cursor()
                user_id = i[0]
                end_ts = i[4]
                now_ts = int(time.time())
                if now_ts >= end_ts:
                    cur.execute('UPDATE users SET pay_status = 0 WHERE user_id = ?', (user_id,))
                    cur.execute('UPDATE users SET end_pay = 0 WHERE user_id = ?', (user_id,))
                    connection.commit()
                connection.close()
                time.sleep(1.5)
            except:
                pass

newMonitoring()
