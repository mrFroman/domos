import time

from bot.tgbot.databases.database import DatabaseConnection
from config import MAIN_DB_PATH


def newMonitoring():
    """Мониторинг и удаление истекших событий"""
    while True:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main")
        data = db.fetchall('SELECT * FROM events')
        for i in data:
            try:
                if isinstance(i, dict):
                    event_id = i.get('event_id', '')
                    end_ts = i.get('date', 0)
                else:
                    event_id = i[0] if len(i) > 0 else ''
                    end_ts = i[2] if len(i) > 2 else 0
                
                now_ts = int(time.time())
                if now_ts >= end_ts:
                    db.execute('DELETE FROM events WHERE event_id = %s', (event_id,))
            except:
                pass
        time.sleep(120)


newMonitoring()
