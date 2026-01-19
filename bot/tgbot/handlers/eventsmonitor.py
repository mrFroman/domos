import sqlite3
import time
from pathlib import Path
path = str(Path(__file__).parents[2])


users_db_path = f'{path}/tgbot/databases/data.db'


def newMonitoring():
    while True:
        connection = sqlite3.connect(users_db_path)
        cur = connection.cursor()
        data = cur.execute('SELECT * FROM events').fetchall()
        connection.close()
        for i in data:
            try:
                event_id = i[0]
                end_ts = i[2]
                now_ts = int(time.time())
                if now_ts >= end_ts:
                    cur.execute(
                        'DELETE FROM events WHERE event_id = ?', (event_id,))
                    connection.commit()
                connection.close()
            except:
                pass
        time.sleep(120)


newMonitoring()
