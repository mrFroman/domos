import time
import json
import os
import requests
import sqlite3
import uuid
import datetime
from datetime import timezone

from config import BASE_DIR, MAIN_DB_PATH, load_config, logger_bot


config = load_config(os.path.join(BASE_DIR, ".env"))
token = config.tg_bot.token


def get_rec_payment(user_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = (
        sqlite_connection.cursor()
        .execute(
            "SELECT * FROM rec_payments WHERE user_id = ? AND status = ?",
            (user_id, "active"),
        )
        .fetchall()
    )
    sqlite_connection.commit()
    sqlite_connection.close()
    return info


def createRecurrentPayment(payment_id, amount, user_id):
    """Создает запись о рекуррентном платеже в БД"""
    try:
        created_at = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
        sqlite_connection.cursor().execute(
            """
            INSERT INTO rec_payments (
                user_id, amount, currency, is_recurrent, status,
                rebill_id, payment_id_last, start_pay_date, end_pay_date,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                amount,
                "RUB",
                1,  # is_recurrent = 1
                "pending",  # status = 0 (не оплачен)
                None,  # rebill_id будет обновлен в вебхуке
                payment_id,
                None,  # start_pay_date будет обновлен в вебхуке
                None,  # end_pay_date будет обновлен в вебхуке
                created_at,  # дата создания записи
            ),
        )
        sqlite_connection.commit()
        sqlite_connection.close()
        logger_bot.info(
            f"Создан платёж в БД с payment_id {payment_id}, для пользователя {user_id}",
        )
    except Exception as e:
        logger_bot.error("SQL ERROR " + str(e))


def get_user_by_user_id(user_id):
    try:
        sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
        sqlite_connection.row_factory = sqlite3.Row
        cursor = sqlite_connection.cursor()

        # Ищем пользователя в БД
        cursor.execute(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )
        user = cursor.fetchone()

        # Формируем словарь с данными
        if user:
            return dict(user)
        return {}

    except Exception as e:
        logger_bot.error(f"Ошибка при получении данных пользователя: {e}")
        return {}
    finally:
        sqlite_connection.close()


def getAdmins():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        'SELECT user_id FROM users WHERE rank = 1').fetchall()
    sqlite_connection.close()
    return info


def save_request_to_db(
    request_type: str,
    request_date: datetime,
    request_text: str,
    user_full_name: str,
    user_username: str
):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    cursor = sqlite_connection.cursor()

    cursor.execute('''
        INSERT INTO requests (
            request_type,
            request_date,
            request_text,
            user_full_name,
            user_username
        ) VALUES (?, ?, ?, ?, ?)
    ''', (
        request_type,
        # SQLite expects str for datetime
        request_date.strftime("%Y-%m-%d %H:%M:%S"),
        request_text,
        user_full_name,
        user_username
    ))

    sqlite_connection.commit()
    sqlite_connection.close()


def get_user_info(user_id: int) -> dict:
    """Получает информацию о пользователе из БД"""
    try:
        sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
        cursor = sqlite_connection.cursor()

        # Ищем пользователя в БД
        cursor.execute(
            'SELECT full_name, fullName FROM users WHERE user_id = ?',
            (user_id,)
        )
        user_data = cursor.fetchone()

        # Формируем словарь с данными
        if user_data:
            return {
                'full_name': user_data[0],
                'fullName': user_data[1]
            }
        return {}

    except Exception as e:
        logger_bot.error(f"Ошибка при получении данных пользователя: {e}")
        return {}
    finally:
        sqlite_connection.close()


def update_user_full_name(user_id: int, name: str):
    """
    Обновляет поле full_name для всех записей с указанным user_id

    :param user_id: ID пользователя для поиска
    :param name: Новое значение для поля full_name
    :param db_path: Путь к файлу базы данных
    :return: Количество обновленных строк
    """
    try:
        # Подключаемся к базе данных
        sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
        cursor = sqlite_connection.cursor()

        # Выполняем UPDATE запрос
        cursor.execute(
            "UPDATE users SET full_name = ? WHERE user_id = ?",
            (name, user_id))

        # Получаем количество измененных строк
        rows_updated = cursor.rowcount

        # Фиксируем изменения и закрываем соединение
        sqlite_connection.commit()
        sqlite_connection.close()

        return rows_updated

    except sqlite3.Error as error:
        logger_bot.error(f"Ошибка при работе с SQLite: {error}")
        return 0


def get_user_full_name(user_id: int) -> str:
    try:
        sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
        cursor = sqlite_connection.cursor()
        cursor.execute(
            "SELECT full_name FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        sqlite_connection.close()
        return result[0] if result and result[0] else ''
    except sqlite3.Error as error:
        logger_bot.error(f"Ошибка при получении ФИО: {error}")
        return ''


def get_rieltor_data(user_id: int) -> dict:
    """Получает данные риелтора из БД"""
    conn = sqlite3.connect(MAIN_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT last_name, first_name, middle_name, passport_series, passport_number, "
        "birth_date, birth_place, issued_by, issue_date, department_code, registration_address "
        "FROM passport_data WHERE user_id = ? AND role = 'rieltor'",
        (user_id,)
    )
    data = cursor.fetchone()
    conn.close()

    if not data:
        return {}

    return {
        'last_name': data[0],
        'first_name': data[1],
        'middle_name': data[2],
        'passport_series': data[3],
        'passport_number': data[4],
        'birth_date': data[5],
        'birth_place': data[6],
        'issued_by': data[7],
        'issue_date': data[8],
        'department_code': data[9],
        'registration_address': data[10]
    }


def get_last_client_data(user_id: int) -> dict:
    """Получает данные последнего клиента риелтора"""
    conn = sqlite3.connect(MAIN_DB_PATH)
    cursor = conn.cursor()
    user_id1 = f"{user_id}_client"
    cursor.execute(
        "SELECT last_name, first_name, middle_name, passport_series, passport_number, "
        "birth_date, birth_place, issued_by, issue_date, department_code, registration_address "
        "FROM passport_data WHERE user_id = ? AND role = 'client' "
        "ORDER BY CAST(SUBSTR(client_id, INSTR(client_id, '_') + 1) AS INTEGER) DESC LIMIT 1",
        (user_id1,)
    )
    data = cursor.fetchone()
    conn.close()

    if not data:
        return {}

    return {
        'last_name': data[0],
        'first_name': data[1],
        'middle_name': data[2],
        'passport_series': data[3],
        'passport_number': data[4],
        'birth_date': data[5],
        'birth_place': data[6],
        'issued_by': data[7],
        'issue_date': data[8],
        'department_code': data[9],
        'registration_address': data[10]
    }


def update_passport_data(user_id: int, field: str, new_value: str, is_client: bool = False):
    """Обновляет данные паспорта в БД"""
    conn = sqlite3.connect(MAIN_DB_PATH)
    cursor = conn.cursor()

    if is_client:
        # Для клиента обновляем последнюю запись
        user_id1 = f"{user_id}_client"
        cursor.execute(
            f"UPDATE passport_data SET {field} = ? "
            "WHERE user_id = ? AND role = 'client' "
            "ORDER BY CAST(SUBSTR(client_id, INSTR(client_id, '_') + 1) AS INTEGER) DESC LIMIT 1",
            (new_value, user_id1)
        )
    else:
        # Для риелтора
        cursor.execute(
            f"UPDATE passport_data SET {field} = ? "
            "WHERE user_id = ? AND role = 'rieltor'",
            (new_value, user_id)
        )

    conn.commit()
    conn.close()


# Форматирование данных
def format_passport_data(data: dict, prefix: str = "") -> str:
    """Форматирует данные паспорта в читаемый вид"""
    return (
        f"👤 ФИО: {data['last_name']} {data['first_name']} {data['middle_name']}\n"
        f"🔢 Серия/номер: {data['passport_series']} {data['passport_number']}\n"
        f"🎂 Дата рождения: {data['birth_date']}\n"
        f"📍 Место рождения: {data['birth_place']}\n"
        f"🏛 Выдан: {data['issued_by']}\n"
        f"📅 Дата выдачи: {data['issue_date']}\n"
        f"🔐 Код подразделения: {data['department_code']}\n"
        f"🏠 Адрес регистрации: {data['registration_address']}"
    )


def get_realtor_and_last_client_data(user_id: int):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    cursor = sqlite_connection.cursor()

    try:
        # Получаем данные риелтора
        cursor.execute("""
            SELECT * FROM passport_data 
            WHERE user_id = ? AND role = 'rieltor'
        """, (user_id,))
        realtor_row = cursor.fetchone()

        # Получаем имена столбцов
        realtor_columns = [column[0] for column in cursor.description]
        realtor_data = dict(zip(realtor_columns, realtor_row)
                            ) if realtor_row else None

        # Получаем данные последнего клиента
        cursor.execute("""
            SELECT last_name, first_name, middle_name 
            FROM passport_data 
            WHERE user_id LIKE ? 
            ORDER BY CAST(SUBSTR(client_id, INSTR(client_id, '_') + 1) AS INTEGER) DESC 
            LIMIT 1
        """, (f"{user_id}_%",))
        client_row = cursor.fetchone()

        # Получаем имена столбцов
        client_columns = [column[0] for column in cursor.description]
        client_data = dict(zip(client_columns, client_row)
                           ) if client_row else None

        return realtor_data, client_data

    except Exception as e:
        logger_bot.error(
            f"Ошибка при получении данных риелтора и клиента: {e}")
        return None, None
    finally:
        sqlite_connection.close()


def save_passport(passport_data: dict, user_id, registration_data: dict, is_client):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    cursor = sqlite_connection.cursor()
    logger_bot.info(f"Сохраняем паспортные данные в БД")

    try:
        client_id = None
        if is_client:
            # Получаем текущее количество клиентов у этого риелтора
            cursor.execute(
                "SELECT COUNT(*) FROM passport_data WHERE user_id = ? AND role LIKE 'client%'",
                (user_id,)
            )
            count = cursor.fetchone()[0]
            client_id = f"client_{count + 1}"

            # Проверяем уникальность (на всякий случай)
            cursor.execute(
                "SELECT 1 FROM passport_data WHERE user_id = ? AND client_id = ?",
                (user_id, client_id)
            )
            if cursor.fetchone():
                # Если вдруг ID существует (маловероятно), добавляем случайный суффикс
                client_id = f"client_{count + 1}_{uuid.uuid4().hex[:2]}"

        # Формируем данные для вставки
        raw_passport_number = passport_data.get('passport_number', '') or ''
        tokens = str(raw_passport_number).split()
        passport_series_value = tokens[0] if len(tokens) > 0 else ''
        passport_number_value = tokens[1] if len(tokens) > 1 else ''
        data = [
            user_id,
            client_id,
            passport_data.get('last_name', ''),
            passport_data.get('first_name', ''),
            passport_data.get('middle_name', ''),
            passport_series_value,
            passport_number_value,
            passport_data.get('department_code', ''),
            passport_data.get('birth_date', ''),
            passport_data.get('birth_place', ''),
            passport_data.get('issue_date', ''),
            passport_data.get('issued_by', ''),
            registration_data.get('registration_adress', ''),
            'client' if is_client else 'rieltor'
        ]
        logger_bot.info(f"Данные для сохраненияв БД: {data}")

        # Удаляем None для client_id если это риелтор
        if not is_client:
            data[1] = None

        cursor.execute("""
            INSERT INTO passport_data 
            (user_id, client_id, last_name, first_name, middle_name, 
             passport_series, passport_number, department_code, birth_date, 
             birth_place, issue_date, issued_by, registration_address, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)

        sqlite_connection.commit()
        return client_id  # Для клиентов вернет client_1, client_2 и т.д.

    except Exception as e:
        logger_bot.error(f"Ошибка при сохранении паспорта: {e}")
        return None
    finally:
        sqlite_connection.close()


def check_passport_client_exists(user_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH
                                        )
    cursor = sqlite_connection.cursor()

    try:
        # Получаем последнюю запись паспорта для данного user_id
        cursor.execute("""
            SELECT last_name, first_name, middle_name 
            FROM passport_data 
            WHERE user_id LIKE ? 
            ORDER BY CAST(SUBSTR(client_id, INSTR(client_id, '_') + 1) AS INTEGER) DESC 
            LIMIT 1
        """, (f"{user_id}_%",))  # Используем LIKE для поиска по шаблону

        result = cursor.fetchone()

        if result:
            # Если запись найдена, объединяем фамилию, имя и отчество в одну строку
            last_name, first_name, middle_name = result
            full_name = f"{last_name} {first_name} {middle_name}"
            return full_name
        else:
            # Если записи нет, возвращаем 1
            return 1

    except Exception as e:
        logger_bot.error(f"Ошибка при получении данных паспорта: {e}")
        return 1  # Возвращаем 1 в случае ошибки
    finally:
        sqlite_connection.close()


def check_passport_exists(user_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    cursor = sqlite_connection.cursor()

    try:
        # Проверяем, есть ли данные паспорта для данного user_id
        cursor.execute("""
            SELECT COUNT(*) FROM passport_data 
            WHERE user_id = ? AND 
            last_name IS NOT NULL AND 
            first_name IS NOT NULL AND 
            middle_name IS NOT NULL AND 
            passport_series IS NOT NULL AND 
            passport_number IS NOT NULL
        """, (user_id,))

        count = cursor.fetchone()[0]
        return count > 0  # Если есть хотя бы одна запись, возвращаем True

    except Exception as e:
        logger_bot.error(f"Ошибка при проверке паспорта: {e}")
        return False
    finally:
        sqlite_connection.close()


def getUnpaids():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        'SELECT fullName FROM users WHERE pay_status = 0').fetchall()
    sqlite_connection.close()
    return info


def sendLogToAdm(text):
    admins = getAdmins()
    for i in admins:
        requests.get(
            f'https://api.telegram.org/bot{token}/sendMessage?chat_id={i[0]}&text={text}&parse_mode=HTML')
        logger_bot.info(f'Сообщение отправлено админу {i[0]}')


def sendLogToAdmMk(text, mk):
    admins = getAdmins()
    for i in admins:
        requests.get(
            f'https://api.telegram.org/bot{token}/sendMessage?chat_id={i[0]}&text={text}&reply_markup={mk}&parse_mode=HTML')
        logger_bot.info(f'Сообщение отправлено админу {i[0]}')


def sendLogToUser(text, user_id):
    requests.get(
        f'https://api.telegram.org/bot{token}/sendMessage?chat_id={user_id}&text={text}&parse_mode=HTML')
    logger_bot.info(f'Сообщение отправлено пользователю {user_id}')


def sendMsgPhoto(text, user_id, photo):
    logrs = requests.get(
        f'https://api.telegram.org/bot{token}/sendPhoto?chat_id={user_id}&photo={photo}&caption={text}&parse_mode=HTML')
    dictData = json.loads((logrs.text))
    return (dictData['ok'])

def sendMsgVideo(text, user_id, video):
    logrs = requests.get(
        f'https://api.telegram.org/bot{token}/sendVideo?chat_id={user_id}&video={video}&caption={text}&parse_mode=HTML'
    )
    dictData = json.loads(logrs.text)
    return dictData['ok']
def checkUserAdmin(user_id):
    exists = checkUserExists(user_id)
    if exists == 'exists':
        sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
        info = str(sqlite_connection.cursor().execute(
            'SELECT rank FROM users WHERE user_id = ?', (user_id, )).fetchone()[0])
        if info == '1':
            return 'admin'
        else:
            return 'user'
    else:
        return 'user'


def checkAdminLink(linkid):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    try:
        info = str(sqlite_connection.cursor().execute(
            'SELECT activated FROM admin WHERE link_id = ?', (linkid,)).fetchone()[0])
        if info == '1':
            sqlite_connection.close()
            return 'alreadyactivated'
        else:
            sqlite_connection.close()
            return 'successAdmined'
    except:
        return '404'


def checkRefLink(linkid, user_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    exists = checkUserExists(linkid)
    if exists == 'exists':
        info = sqlite_connection.cursor().execute(
            "INSERT INTO refferal VALUES (?, ?)", (linkid, user_id,))
        sqlite_connection.commit()
        sqlite_connection.close()
        return 'successreferaled'
    else:
        sqlite_connection.close()
        return 'error404'


def getAdminLink():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = str(sqlite_connection.cursor().execute(
        'SELECT link_id FROM admin').fetchone()[0])
    sqlite_connection.close()
    return info


def getUserEndPay(user_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = int(sqlite_connection.cursor().execute(
        'SELECT end_pay FROM users WHERE user_id = ?', (user_id,)).fetchone()[0])
    sqlite_connection.close()
    return info


def checkUserExists(user_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        'SELECT * FROM users WHERE user_id = ?', (user_id, )).fetchone()
    if info is None:
        sqlite_connection.close()
        return ('empty')
    else:
        sqlite_connection.close()
        return 'exists'


def getBannedUserId(user_id):
    exists = checkUserExists(user_id)
    if exists == 'exists':
        sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
        info = int(sqlite_connection.cursor().execute(
            'SELECT banned FROM users WHERE user_id = ?', (user_id,)).fetchone()[0])
        sqlite_connection.close()
        return info
    else:
        return 0


def checkUserExistsUsername(username):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        'SELECT * FROM users WHERE fullName = ?', (username, )).fetchone()
    if info is None:
        sqlite_connection.close()
        return 'empty', 'empty', 'empty', 'empty'
    else:
        user_id = info[0]
        pay_status = info[1]
        rank = info[3]
        sqlite_connection.close()
        return user_id, pay_status, rank, username


def regUser(user_id, username):
    try:
        sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
        sqlite_connection.cursor().execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                           (user_id, 0, 0, 0, 0, username, 0, 0, 0,))
        sqlite_connection.commit()
        sqlite_connection.close()
        sendLogToAdm(
            f'<i>Новый юзер в боте:</i> @{username} | <code>{user_id}</code>')

    except Exception as e:
        logger_bot.error('SQL ERROR ' + str(e))


def changeSomeUserParam(user_id, param, paramNew):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    sqlite_connection.cursor().execute(
        f'UPDATE users SET {param} = ? WHERE user_id = ?', (paramNew, user_id,))
    sqlite_connection.commit()
    sqlite_connection.close()


def changeUsername(user_id, username):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    sqlite_connection.cursor().execute(
        'UPDATE users SET fullName = ? WHERE user_id = ?', (username, user_id,))
    sqlite_connection.commit()
    sqlite_connection.close()


def banUser(user_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    sqlite_connection.cursor().execute(
        'UPDATE users SET banned = 1 WHERE user_id = ?', (user_id,))
    sqlite_connection.commit()
    sqlite_connection.close()


def unbanUser(user_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    sqlite_connection.cursor().execute(
        'UPDATE users SET banned = 0 WHERE user_id = ?', (user_id,))
    sqlite_connection.commit()
    sqlite_connection.close()


def changeUserAdminLink(user_id, status, string):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    sqlite_connection.cursor().execute(
        'UPDATE users SET rank = ? WHERE user_id = ?', (status, user_id,))
    sqlite_connection.cursor().execute('UPDATE admin SET activated = 1')
    sqlite_connection.commit()
    sqlite_connection.cursor().execute('UPDATE admin SET link_id = ?', (string,))
    sqlite_connection.cursor().execute('UPDATE admin SET activated = 0')
    sqlite_connection.commit()
    sqlite_connection.close()


def takeUserSub(user_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    sqlite_connection.cursor().execute(
        'UPDATE users SET pay_status = 0 WHERE user_id = ?', (user_id,))
    sqlite_connection.cursor().execute(
        'UPDATE users SET last_pay = 0 WHERE user_id = ?', (user_id,))
    sqlite_connection.cursor().execute(
        'UPDATE users SET end_pay = 0 WHERE user_id = ?', (user_id,))
    sqlite_connection.commit()
    sqlite_connection.close()


def changeUserAdmin(user_id):
    now = checkUserAdmin(user_id)
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    if now == 'admin':
        sqlite_connection.cursor().execute(
            'UPDATE users SET rank = 0 WHERE user_id = ?', (user_id,))
        sqlite_connection.commit()
        sqlite_connection.close()
        return 'usered'
    else:
        sqlite_connection.cursor().execute(
            'UPDATE users SET rank = 1 WHERE user_id = ?', (user_id,))
        sqlite_connection.commit()
        sqlite_connection.close()
        return 'admined'


def createRieltor(rieltor_id, fullname, phone, email, photo):
    try:
        sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
        sqlite_connection.cursor().execute("INSERT INTO rieltors VALUES (?, ?, ?, ?, ?)",
                                           (rieltor_id, fullname, email, photo, phone,))
        sqlite_connection.commit()
        sqlite_connection.close()

    except Exception as e:
        logger_bot.error('SQL ERROR ' + str(e))


def createEvent(event_id, desc, date, title, link, name, photo):
    try:
        sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
        sqlite_connection.cursor().execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
                                           (event_id, desc, date, title, link, name, photo,))
        sqlite_connection.commit()
        sqlite_connection.close()

    except Exception as e:
        logger_bot.error('SQL ERROR ' + str(e))


def createContact(contact_id, fullname, phone, email, photo, job):
    try:
        sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
        sqlite_connection.cursor().execute("INSERT INTO contacts VALUES (?, ?, ?, ?, ?, ?)",
                                           (contact_id, fullname, email, photo, phone, job,))
        sqlite_connection.commit()
        sqlite_connection.close()

    except Exception as e:
        logger_bot.error('SQL ERROR ' + str(e))


def createMeeting(user_id, day, meeting_id, roomnum):
    try:
        sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
        sqlite_connection.cursor().execute("INSERT INTO meetings VALUES (?, ?, ?, ?, ?, ?)",
                                           (meeting_id, user_id, 0, day, 'None', int(roomnum)))
        sqlite_connection.commit()
        sqlite_connection.close()

    except Exception as e:
        logger_bot.error('SQL ERROR ' + str(e))


def checkRoom(meeting_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = str(sqlite_connection.cursor().execute(
        'SELECT roomnum FROM meetings WHERE meeting_id = ?', (meeting_id, )).fetchone()[0])
    sqlite_connection.close()

    return info


def checkmeetingid(user_id, date, roomnum, time):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    cursor = sqlite_connection.cursor()
    query = '''
            SELECT meeting_id FROM meetings 
            WHERE user_id = ? AND roomnum = ? AND date = ? AND times LIKE ?
        '''
    cursor.execute(query, (user_id, roomnum, date, f'%{time}%'))
    info = cursor.fetchone()[0]
    sqlite_connection.close()
    return info


def checkTimes(meeting_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = str(sqlite_connection.cursor().execute(
        'SELECT times FROM meetings WHERE meeting_id = ?', (meeting_id, )).fetchone()[0])
    sqlite_connection.close()
    print(f'{info=}')
    if info != 'None':
        times = info.split(';')
        try:
            times.remove('')
        except:
            pass
        return info
    else:
        return 'Empty'


def editTimes(meeting_id, time, roomnum):
    now_time = checkTimes(meeting_id)
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    if time not in now_time:
        if now_time == 'Empty':
            date = str(checkMeetingDay(meeting_id, roomnum))
            info = checkTimeExists(time, date, roomnum)
            try:
                print(info[0])
                return 'busied'
            except:
                sqlite_connection.cursor().execute('UPDATE meetings SET times = ? WHERE meeting_id = ? AND roomnum = ?', (time, meeting_id, roomnum))
        else:
            date = str(checkMeetingDay(meeting_id, roomnum))
            info = checkTimeExists(time, date, roomnum)
            try:
                print(info[0])
                return 'busied'
            except:
                finish = now_time + time
                sqlite_connection.cursor().execute('UPDATE meetings SET times = ? WHERE meeting_id = ? AND roomnum = ?', (finish, meeting_id, roomnum))
    else:
        now_time = now_time.split(';')
        now_time.remove(time.replace(';', ''))
        full_data = ';'.join(now_time)
        if full_data == '':
            full_data = 'None'
        sqlite_connection.cursor().execute('UPDATE meetings SET times = ? WHERE meeting_id = ? AND roomnum = ?', (str(full_data), meeting_id, roomnum))
    sqlite_connection.commit()
    sqlite_connection.close()


def checkMeetingDay(meeting_id, roomnum):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    query = f"SELECT date FROM meetings WHERE meeting_id = '{meeting_id}' AND roomnum = {roomnum}"
    info = sqlite_connection.cursor().execute(query).fetchone()[0]
    sqlite_connection.commit()
    sqlite_connection.close()
    return info


def deleteMeeting(meeting_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    try:
        meeting_id = str(meeting_id)
        cursor = sqlite_connection.cursor()
        # Безопасный вариант с параметризованным запросом (рекомендуется)
        query = "DELETE FROM meetings WHERE meeting_id = ?"
        cursor.execute(query, (meeting_id,))
        sqlite_connection.commit()
        return True  # Успешное удаление
    except Exception as e:
        logger_bot.error(f"Ошибка при удалении встречи: {e}")
        return False  # Ошибка при удалении
    finally:
        sqlite_connection.close()


def getRieltorId(id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        'SELECT * FROM rieltors WHERE id = ?', (id,)).fetchone()
    sqlite_connection.commit()
    sqlite_connection.close()
    return info


def getEventId(id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        'SELECT * FROM events WHERE event_id = ?', (id,)).fetchone()
    sqlite_connection.commit()
    sqlite_connection.close()
    return info


def getContactId(id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        'SELECT * FROM contacts WHERE id = ?', (id,)).fetchone()
    sqlite_connection.commit()
    sqlite_connection.close()
    return info


def getUserById(id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        'SELECT fullname FROM users WHERE user_id = ?', (id,)).fetchone()[0]
    sqlite_connection.commit()
    sqlite_connection.close()
    return info


def checkTimeExists(time, day, roomnum):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    query = f"SELECT times FROM meetings WHERE date = '{day}' AND times LIKE '%{time}%' and roomnum = {roomnum}"
    info = sqlite_connection.cursor().execute(query).fetchall()
    sqlite_connection.commit()
    sqlite_connection.close()
    return info


def checkTimeExists1(day, roomnum):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    cursor = sqlite_connection.cursor()

    # Получаем все занятые времена и соответствующие user_id
    query = f"SELECT times, user_id FROM meetings WHERE date = ? AND roomnum = ?"
    cursor.execute(query, (day, roomnum))
    time_user_pairs = cursor.fetchall()

    # Создаем словарь {время: имя_пользователя}
    occupied_times = {}
    for time_slots, user_id in time_user_pairs:
        if not time_slots:
            continue

        # Получаем имя пользователя
        cursor.execute(
            "SELECT fullName FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        user_name = user_row[0] if user_row else "Неизвестный пользователь"

        # Разбиваем по `;` и сохраняем каждое время отдельно
        for slot in time_slots.split(';'):
            cleaned_slot = slot.strip()
            if cleaned_slot:  # Игнорируем пустые строки
                occupied_times[cleaned_slot] = user_name

    cursor.close()
    sqlite_connection.close()
    return occupied_times


def getAllMeetings():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    query = f"SELECT * FROM meetings"
    rows = sqlite_connection.cursor().execute(query).fetchall()
    sqlite_connection.close()
    return rows


def makeMeetCompleted(meeting_id, username, roomnum):
    day = str(checkMeetingDay(meeting_id, roomnum))
    times = checkTimes(meeting_id).split(';')
    full_data = ' '.join(times)
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    sqlite_connection.cursor().execute(
        'UPDATE meetings SET status = 1 WHERE meeting_id = ? AND roomnum = ?', (meeting_id, roomnum))
    # sendLogToAdm(f'Пользователь @{username} забронировал переговорную на {day} на время: {full_data}')
#    users = getAllUsersForAd()
#    for i in users:
#        res = sendLogToUser(f'Пользователь @{username} забронировал переговорную на {day} на время: {full_data}', i[0])
    sqlite_connection.commit()
    sqlite_connection.close()


def getRieltors():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    query = "SELECT * FROM rieltors ORDER BY fullName"
    info = sqlite_connection.cursor().execute(query).fetchall()
    sqlite_connection.commit()
    sqlite_connection.close()
    return info


def getEvents():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    # Сортировка по возрастанию времени
    query = "SELECT * FROM events ORDER BY date ASC"
    info = sqlite_connection.cursor().execute(query).fetchall()
    sqlite_connection.commit()
    sqlite_connection.close()
    return info


def getContacts():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    query = "SELECT * FROM contacts"
    info = sqlite_connection.cursor().execute(query).fetchall()
    sqlite_connection.commit()
    sqlite_connection.close()
    return info


def getUserPay(user_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        "SELECT pay_status FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
    sqlite_connection.commit()
    sqlite_connection.close()
    return int(info)


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


def getPaidUsersCount():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = int(sqlite_connection.cursor().execute(
        "SELECT COUNT(*) FROM users WHERE pay_status = 1").fetchone()[0])
    sqlite_connection.close()
    return (info)


def getPaidUsers():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        "SELECT fullName FROM users WHERE pay_status = 1").fetchall()
    sqlite_connection.close()
    return (info)


def getPaidUsersForAd():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        "SELECT user_id FROM users WHERE pay_status = 1").fetchall()
    sqlite_connection.close()
    return (info)


def getFreeUsersForAd():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        "SELECT user_id FROM users WHERE pay_status = 0").fetchall()
    sqlite_connection.close()
    return (info)


def delRietlor(rieltor_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    sqlite_connection.cursor().execute(
        "DELETE FROM rieltors WHERE id = ?", (rieltor_id,))
    sqlite_connection.commit()
    sqlite_connection.close()


def delContact(contact_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    sqlite_connection.cursor().execute(
        "DELETE FROM contacts WHERE id = ?", (contact_id,))
    sqlite_connection.commit()
    sqlite_connection.close()


def delEvent(event_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    sqlite_connection.cursor().execute(
        "DELETE FROM events WHERE event_id = ?", (event_id,))
    sqlite_connection.commit()
    sqlite_connection.close()


def getAllUsersForAd():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        "SELECT user_id FROM users").fetchall()
    sqlite_connection.close()
    return (info)


def getAllUsersForApi():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute("SELECT * FROM users").fetchall()
    sqlite_connection.close()
    return (info)


def getAllPaymentsForApi():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        "SELECT * FROM payments ORDER BY ts DESC").fetchall()
    sqlite_connection.close()
    return (info)


def getFreeUsersCount():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = int(sqlite_connection.cursor().execute(
        "SELECT COUNT(*) FROM users WHERE pay_status = 0").fetchone()[0])
    sqlite_connection.close()
    return (info)


def getUsersCount():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = int(sqlite_connection.cursor().execute(
        "SELECT COUNT(*) FROM users").fetchone()[0])
    sqlite_connection.close()
    return (info)


def getPaymentCount():
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = int(sqlite_connection.cursor().execute(
        "SELECT COUNT(*) FROM payments").fetchone()[0])
    sqlite_connection.close()
    return (info)


def getUserRef(user_id):
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    info = sqlite_connection.cursor().execute(
        "SELECT reffer_id FROM refferal WHERE user_id = ?", (user_id,)).fetchone()
    sqlite_connection.close()
    if info != None:
        reffer_id = int(info[0])
        return reffer_id
    else:
        return '404'


def giveUserSub(user_id, months):
    int(user_id)
    int(months)
    t = datetime.date.today()
    now_ts = int(time.time())
    t = datetime.date.today()
    n = t.replace(t.year, months, 1)
    timestamp2 = time.mktime(n.timetuple())

    if now_ts > timestamp2:
        n = t.replace(t.year+1, months, 1)
        timestamp2 = time.mktime(n.timetuple())
    else:
        n = t.replace(t.year, months, 1)
        timestamp2 = time.mktime(n.timetuple())

    timestamp2 = int(timestamp2)
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    sqlite_connection.cursor().execute(
        'UPDATE users SET last_pay = ? WHERE user_id = ?', (now_ts, user_id,))
    sqlite_connection.commit()
    sqlite_connection.cursor().execute(
        'UPDATE users SET end_pay = ? WHERE user_id = ?', (timestamp2, user_id,))
    sqlite_connection.commit()
    sqlite_connection.cursor().execute(
        'UPDATE users SET pay_status = 1 WHERE user_id = ?', (user_id,))
    sqlite_connection.commit()
    sqlite_connection.close()


def makePaymentCompleted(id):
    user_id, amount, created, status = getPayment(id)
    sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
    t = datetime.date.today()
    now_ts = int(time.time())
    current_datetime = datetime.now()
    day = current_datetime.day

    if amount == 10000:
        t = datetime.date.today()
        if day >= 20:
            n = t.replace(t.year, 2, 1)
        else:
            n = t.replace(t.year, 1, 1)

        timestamp2 = time.mktime(n.timetuple())
        if now_ts > timestamp2:
            n = t.replace(t.year+1, 1, 1)
            timestamp2 = time.mktime(n.timetuple())
    elif amount == 12897:
        t = datetime.date.today()
        if day >= 17:
            n = t.replace(t.year, 2, 1)
        else:
            n = t.replace(t.year, 1, 1)

        timestamp2 = time.mktime(n.timetuple())
        if now_ts > timestamp2:
            n = t.replace(t.year+1, 1, 1)
            timestamp2 = time.mktime(n.timetuple())

    elif amount == 60000:
        t = datetime.date.today()
        n = t.replace(t.year, 6, 1)
        timestamp2 = time.mktime(n.timetuple())
        if now_ts > timestamp2:
            n = t.replace(t.year+1, 1, 1)
            timestamp2 = time.mktime(n.timetuple())
    elif amount == 30000:
        t = datetime.date.today()
        n = t.replace(t.year, 3, 1)
        timestamp2 = time.mktime(n.timetuple())
        if now_ts > timestamp2:
            n = t.replace(t.year+1, 1, 1)
            timestamp2 = time.mktime(n.timetuple())

    elif amount == 120000:
        t = datetime.date.today()
        n = t.replace(t.year, 12, 1)
        timestamp2 = time.mktime(n.timetuple())
        if now_ts > timestamp2:
            n = t.replace(t.year+1, 1, 1)
            timestamp2 = time.mktime(n.timetuple())

    ref = getUserRef(user_id)

    if status == 0:
        aa = sqlite_connection.cursor().execute(
            'UPDATE payments SET status = 1 WHERE payment_id = ?', (id,))
        sqlite_connection.cursor().execute(
            'UPDATE users SET last_pay = ? WHERE user_id = ?', (now_ts, user_id,))
        sqlite_connection.cursor().execute(
            'UPDATE users SET end_pay = ? WHERE user_id = ?', (timestamp2, user_id,))
        sqlite_connection.cursor().execute(
            'UPDATE users SET pay_status = 1 WHERE user_id = ?', (user_id,))
        if ref == '404':
            pass
        else:
            end_ts = datetime.fromtimestamp(getUserEndPay(ref))
            month = end_ts.strftime('%m')
            year = int(end_ts.strftime('%Y'))
            if month != '12':
                month = int(month) + 1

            else:
                year = int(end_ts.strftime('%Y')) + 1
                month = 1

        if user_id != ref:
            new_dt = f'{year}-01-{month} 00:00:00'
            datetime_object = datetime.strptime(
                new_dt, '%Y-%d-%m %H:%M:%S')
            timestamp = int(round(datetime_object.timestamp()))
            sqlite_connection.cursor().execute(
                'UPDATE users SET end_pay = ? WHERE user_id = ?', (timestamp, ref,))
            sendLogToUser(
                f'Ваш рефферал с ID {user_id} купил подписку, к вашей подписке добавлен 1 месяц.', ref)
            sqlite_connection.commit()
            sqlite_connection.close()


def createPayment(id, amount, user_id):
    now_ts = int(time.time())
    try:
        sqlite_connection = sqlite3.connect(MAIN_DB_PATH)
        sqlite_connection.cursor().execute(
            "INSERT INTO payments VALUES (?, ?, ?, ?, 0)", (user_id, id, amount, now_ts,))
        sqlite_connection.commit()
        sqlite_connection.close()

    except Exception as e:
        logger_bot.error('SQL ERROR ' + str(e))
