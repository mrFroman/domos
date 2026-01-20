import time

from bot.tgbot.databases.database import DatabaseConnection
from config import MAIN_DB_PATH

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
    """Мониторинг истекших подписок"""
    while True:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main")
        data = db.fetchall('SELECT * FROM users WHERE end_pay != 0')
        for i in data:
            try:
                if isinstance(i, dict):
                    user_id = i.get('user_id', '')
                    end_ts = i.get('end_pay', 0)
                else:
                    user_id = i[0] if len(i) > 0 else ''
                    end_ts = i[4] if len(i) > 4 else 0
                
                now_ts = int(time.time())
                if now_ts >= end_ts:
                    db.execute('UPDATE users SET pay_status = 0 WHERE user_id = %s', (user_id,))
                    db.execute('UPDATE users SET end_pay = 0 WHERE user_id = %s', (user_id,))
                time.sleep(1.5)
            except:
                pass

newMonitoring()
