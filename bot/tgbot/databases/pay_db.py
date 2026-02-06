import time
import json
import os
import requests
import uuid
import datetime
from datetime import timezone

from config import BASE_DIR, MAIN_DB_PATH, DB_TYPE, load_config, logger_bot


config = load_config(os.path.join(BASE_DIR, ".env"))
token = config.tg_bot.token


def get_rec_payment(user_id):
    """Получает активные рекуррентные платежи пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchall(
        "SELECT * FROM rec_payments WHERE user_id = ? AND status = ?",
        (user_id, "active"),
    )
    return info


def createRecurrentPayment(payment_id, amount, user_id):
    """Создает запись о рекуррентном платеже в БД"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    try:
        created_at = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        db.execute(
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
        logger_bot.info(
            f"Создан платёж в БД с payment_id {payment_id}, для пользователя {user_id}",
        )
    except Exception as e:
        logger_bot.error("SQL ERROR " + str(e))


def get_user_by_user_id(user_id):
    """Получает данные пользователя по user_id"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    try:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        user = db.fetchone(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )

        # Формируем словарь с данными
        if user:
            return dict(user) if isinstance(user, dict) else user
        return {}

    except Exception as e:
        logger_bot.error(f"Ошибка при получении данных пользователя: {e}")
        return {}


def getAdmins():
    """Получает список администраторов"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchall('SELECT user_id FROM users WHERE rank = 1')
    return info


def save_request_to_db(
    request_type: str,
    request_date: datetime,
    request_text: str,
    user_full_name: str,
    user_username: str
):
    """Сохраняет запрос в БД"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    db.execute('''
        INSERT INTO requests (
            request_type,
            request_date,
            request_text,
            user_full_name,
            user_username
        ) VALUES (?, ?, ?, ?, ?)
    ''', (
        request_type,
        # SQLite expects str for datetime, PostgreSQL тоже принимает строку
        request_date.strftime("%Y-%m-%d %H:%M:%S"),
        request_text,
        user_full_name,
        user_username
    ))


def get_user_info(user_id: int) -> dict:
    """Получает информацию о пользователе из БД"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    try:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        user_data = db.fetchone(
            'SELECT full_name, full_name_payments FROM users WHERE user_id = ?',
            (user_id,)
        )

        # Формируем словарь с данными
        if user_data:
            if isinstance(user_data, dict):
                return {
                    'full_name_payments': user_data.get('full_name_payments', ''),
                    'full_name': user_data.get('full_name', '')
                }
            else:
                return {
                    'full_name_payments': user_data[0] if len(user_data) > 0 else '',
                    'full_name': user_data[1] if len(user_data) > 1 else ''
                }
        return {}

    except Exception as e:
        logger_bot.error(f"Ошибка при получении данных пользователя: {e}")
        return {}


def update_user_full_name(user_id: int, name: str):
    """
    Обновляет поле full_name_payments для всех записей с указанным user_id

    :param user_id: ID пользователя для поиска
    :param name: Новое значение для поля full_name_payments
    :return: Количество обновленных строк
    """
    from bot.tgbot.databases.database import DatabaseConnection
    
    try:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        db.execute(
            "UPDATE users SET full_name_payments = ? WHERE user_id = ?",
            (name, user_id))
        return 1  # В PostgreSQL rowcount может работать по-другому, возвращаем 1 при успехе
    except Exception as error:
        logger_bot.error(f"Ошибка при обновлении full_name: {error}")
        return 0


def get_user_full_name(user_id: int) -> str:
    """Получает полное имя пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    try:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        result = db.fetchone(
            "SELECT full_name_payments FROM users WHERE user_id = ?", (user_id,))
        if result:
            if isinstance(result, dict):
                return result.get('full_name_payments', '') or ''
            else:
                return result[0] if result[0] else ''
        return ''
    except Exception as error:
        logger_bot.error(f"Ошибка при получении ФИО: {error}")
        return ''


def get_rieltor_data(user_id: int) -> dict:
    """Получает данные риелтора из БД"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    data = db.fetchone(
        "SELECT last_name, first_name, middle_name, passport_series, passport_number, "
        "birth_date, birth_place, issued_by, issue_date, department_code, registration_address "
        "FROM passport_data WHERE user_id = ? AND role = 'rieltor'",
        (user_id,)
    )

    if not data:
        return {}

    if isinstance(data, dict):
        return data
    else:
        return {
            'last_name': data[0] if len(data) > 0 else '',
            'first_name': data[1] if len(data) > 1 else '',
            'middle_name': data[2] if len(data) > 2 else '',
            'passport_series': data[3] if len(data) > 3 else '',
            'passport_number': data[4] if len(data) > 4 else '',
            'birth_date': data[5] if len(data) > 5 else '',
            'birth_place': data[6] if len(data) > 6 else '',
            'issued_by': data[7] if len(data) > 7 else '',
            'issue_date': data[8] if len(data) > 8 else '',
            'department_code': data[9] if len(data) > 9 else '',
            'registration_address': data[10] if len(data) > 10 else ''
        }


def get_last_client_data(user_id: int) -> dict:
    """Получает данные последнего клиента риелтора"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    user_id1 = f"{user_id}_client"
    # Адаптируем запрос для PostgreSQL (SUBSTR и INSTR работают по-другому)
    if DB_TYPE == "postgres":
        query = """
            SELECT last_name, first_name, middle_name, passport_series, passport_number, 
            birth_date, birth_place, issued_by, issue_date, department_code, registration_address 
            FROM passport_data WHERE user_id = ? AND role = 'client' 
            ORDER BY CAST(SUBSTRING(client_id FROM POSITION('_' IN client_id) + 1) AS INTEGER) DESC LIMIT 1
        """
    else:
        query = """
            SELECT last_name, first_name, middle_name, passport_series, passport_number, 
            birth_date, birth_place, issued_by, issue_date, department_code, registration_address 
            FROM passport_data WHERE user_id = ? AND role = 'client' 
            ORDER BY CAST(SUBSTR(client_id, INSTR(client_id, '_') + 1) AS INTEGER) DESC LIMIT 1
        """
    
    data = db.fetchone(query, (user_id1,))

    if not data:
        return {}

    if isinstance(data, dict):
        return data
    else:
        return {
            'last_name': data[0] if len(data) > 0 else '',
            'first_name': data[1] if len(data) > 1 else '',
            'middle_name': data[2] if len(data) > 2 else '',
            'passport_series': data[3] if len(data) > 3 else '',
            'passport_number': data[4] if len(data) > 4 else '',
            'birth_date': data[5] if len(data) > 5 else '',
            'birth_place': data[6] if len(data) > 6 else '',
            'issued_by': data[7] if len(data) > 7 else '',
            'issue_date': data[8] if len(data) > 8 else '',
            'department_code': data[9] if len(data) > 9 else '',
            'registration_address': data[10] if len(data) > 10 else ''
        }


def update_passport_data(user_id: int, field: str, new_value: str, is_client: bool = False):
    """Обновляет данные паспорта в БД"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)

    if is_client:
        # Для клиента обновляем последнюю запись
        user_id1 = f"{user_id}_client"
        # Адаптируем запрос для PostgreSQL
        if DB_TYPE == "postgres":
            query = f"""
                UPDATE passport_data SET {field} = ? 
                WHERE user_id = ? AND role = 'client' 
                AND id = (
                    SELECT id FROM passport_data 
                    WHERE user_id = ? AND role = 'client' 
                    ORDER BY CAST(SUBSTRING(client_id FROM POSITION('_' IN client_id) + 1) AS INTEGER) DESC 
                    LIMIT 1
                )
            """
            db.execute(query, (new_value, user_id1, user_id1))
        else:
            query = f"""
                UPDATE passport_data SET {field} = ? 
                WHERE user_id = ? AND role = 'client' 
                ORDER BY CAST(SUBSTR(client_id, INSTR(client_id, '_') + 1) AS INTEGER) DESC LIMIT 1
            """
            db.execute(query, (new_value, user_id1))
    else:
        # Для риелтора
        db.execute(
            f"UPDATE passport_data SET {field} = ? WHERE user_id = ? AND role = 'rieltor'",
            (new_value, user_id)
        )


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
    """Получает данные риелтора и последнего клиента"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)

    try:
        # Получаем данные риелтора
        realtor_result = db.fetchone(
            "SELECT * FROM passport_data WHERE user_id = ? AND role = 'rieltor'",
            (user_id,)
        )
        realtor_data = realtor_result if realtor_result else None

        # Получаем данные последнего клиента
        if DB_TYPE == "postgres":
            client_query = """
                SELECT last_name, first_name, middle_name 
                FROM passport_data 
                WHERE user_id LIKE ? 
                ORDER BY CAST(SUBSTRING(client_id FROM POSITION('_' IN client_id) + 1) AS INTEGER) DESC 
                LIMIT 1
            """
        else:
            client_query = """
                SELECT last_name, first_name, middle_name 
                FROM passport_data 
                WHERE user_id LIKE ? 
                ORDER BY CAST(SUBSTR(client_id, INSTR(client_id, '_') + 1) AS INTEGER) DESC 
                LIMIT 1
            """
        client_result = db.fetchone(client_query, (f"{user_id}_%",))
        client_data = client_result if client_result else None

        return realtor_data, client_data

    except Exception as e:
        logger_bot.error(
            f"Ошибка при получении данных риелтора и клиента: {e}")
        return None, None


def save_passport(passport_data: dict, user_id, registration_data: dict, is_client):
    """Сохраняет паспортные данные в БД"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    logger_bot.info(f"Сохраняем паспортные данные в БД")

    try:
        client_id = None
        if is_client:
            # Получаем текущее количество клиентов у этого риелтора
            if DB_TYPE == "postgres":
                result = db.fetchone(
                    "SELECT COUNT(*) FROM passport_data WHERE user_id::text = ? AND role LIKE 'client%'",
                    (user_id,)
                )
            else:
                result = db.fetchone(
                    "SELECT COUNT(*) FROM passport_data WHERE user_id = ? AND role LIKE 'client%'",
                    (user_id,)
                )
            if result:
                if isinstance(result, dict):
                    count = int(list(result.values())[0])
                else:
                    count = int(result[0]) if result[0] else 0
            else:
                count = 0
            client_id = f"client_{count + 1}"

            # Проверяем уникальность (на всякий случай)
            check_result = db.fetchone(
                "SELECT 1 FROM passport_data WHERE user_id = ? AND client_id = ?",
                (user_id, client_id)
            )
            if check_result:
                # Если вдруг ID существует (маловероятно), добавляем случайный суффикс
                client_id = f"client_{count + 1}_{uuid.uuid4().hex[:2]}"

        # Формируем данные для вставки
        raw_passport_number = passport_data.get('passport_number', '') or ''
        tokens = str(raw_passport_number).split()
        passport_series_value = tokens[0] if len(tokens) > 0 else ''
        passport_number_value = tokens[1] if len(tokens) > 1 else ''
        data = (
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
        )
        logger_bot.info(f"Данные для сохранения в БД: {data}")

        db.execute("""
            INSERT INTO passport_data 
            (user_id, client_id, last_name, first_name, middle_name, 
             passport_series, passport_number, department_code, birth_date, 
             birth_place, issue_date, issued_by, registration_address, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)

        return client_id  # Для клиентов вернет client_1, client_2 и т.д.

    except Exception as e:
        logger_bot.error(f"Ошибка при сохранении паспорта: {e}")
        return None


def check_passport_client_exists(user_id):
    """Проверяет существование паспортных данных клиента"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)

    try:
        # Получаем последнюю запись паспорта для данного user_id
        if DB_TYPE == "postgres":
            query = """
                SELECT last_name, first_name, middle_name 
                FROM passport_data 
                WHERE user_id LIKE ? 
                ORDER BY CAST(SUBSTRING(client_id FROM POSITION('_' IN client_id) + 1) AS INTEGER) DESC 
                LIMIT 1
            """
        else:
            query = """
                SELECT last_name, first_name, middle_name 
                FROM passport_data 
                WHERE user_id LIKE ? 
                ORDER BY CAST(SUBSTR(client_id, INSTR(client_id, '_') + 1) AS INTEGER) DESC 
                LIMIT 1
            """
        result = db.fetchone(query, (f"{user_id}_%",))

        if result:
            # Если запись найдена, объединяем фамилию, имя и отчество в одну строку
            if isinstance(result, dict):
                last_name = result.get('last_name', '')
                first_name = result.get('first_name', '')
                middle_name = result.get('middle_name', '')
            else:
                last_name = result[0] if len(result) > 0 else ''
                first_name = result[1] if len(result) > 1 else ''
                middle_name = result[2] if len(result) > 2 else ''
            full_name = f"{last_name} {first_name} {middle_name}"
            return full_name
        else:
            # Если записи нет, возвращаем 1
            return 1

    except Exception as e:
        logger_bot.error(f"Ошибка при получении данных паспорта: {e}")
        return 1  # Возвращаем 1 в случае ошибки


def check_passport_exists(user_id):
    """Проверяет существование полных паспортных данных"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)

    try:
        # Проверяем, есть ли данные паспорта для данного user_id
        result = db.fetchone("""
            SELECT COUNT(*) FROM passport_data 
            WHERE user_id::text = ? AND 
            last_name IS NOT NULL AND 
            first_name IS NOT NULL AND 
            middle_name IS NOT NULL AND 
            passport_series IS NOT NULL AND 
            passport_number IS NOT NULL
        """, (user_id,))

        if result:
            if isinstance(result, dict):
                count = int(list(result.values())[0])
            else:
                count = int(result[0]) if result[0] else 0
            return count > 0  # Если есть хотя бы одна запись, возвращаем True
        return False

    except Exception as e:
        logger_bot.error(f"Ошибка при проверке паспорта: {e}")
        return False


def getUnpaids():
    """Получает список неоплативших пользователей"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchall('SELECT full_name FROM users WHERE pay_status = 0')
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
    """Проверяет, является ли пользователь администратором"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    exists = checkUserExists(user_id)
    if exists == 'exists':
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        result = db.fetchone('SELECT rank FROM users WHERE user_id = ?', (user_id,))
        if result:
            if isinstance(result, dict):
                info = str(result.get('rank', '0'))
            else:
                info = str(result[0]) if result[0] else '0'
            if info == '1':
                return 'admin'
            else:
                return 'user'
    return 'user'


def checkAdminLink(linkid):
    """Проверяет статус админской ссылки"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    try:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        result = db.fetchone('SELECT activated FROM admin WHERE link_id = ?', (linkid,))
        if result:
            if isinstance(result, dict):
                info = str(result.get('activated', '0'))
            else:
                info = str(result[0]) if result[0] else '0'
            if info == '1':
                return 'alreadyactivated'
            else:
                return 'successAdmined'
        return '404'
    except:
        return '404'


def checkRefLink(linkid, user_id):
    """Проверяет и создает реферальную ссылку"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    exists = checkUserExists(linkid)
    if exists == 'exists':
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        db.execute("INSERT INTO refferal VALUES (?, ?)", (linkid, user_id,))
        return 'successreferaled'
    else:
        return 'error404'


def getAdminLink():
    """Получает админскую ссылку"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main")
    result = db.fetchone('SELECT link_id FROM admin')
    if result:
        if isinstance(result, dict):
            return str(result.get('link_id', ''))
        else:
            return str(result[0]) if result[0] else ''
    return ''


def getUserEndPay(user_id):
    """Получает дату окончания подписки пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    result = db.fetchone('SELECT end_pay FROM users WHERE user_id = ?', (user_id,))
    if result:
        if isinstance(result, dict):
            return int(result.get('end_pay', 0))
        else:
            return int(result[0]) if result[0] else 0
    return 0


def checkUserExists(user_id):
    """Проверяет существование пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchone('SELECT * FROM users WHERE user_id = ?', (user_id,))

    if info is None:
        return 'empty'
    else:
        return 'exists'


def getBannedUserId(user_id):
    """Получает статус бана пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    exists = checkUserExists(user_id)
    if exists == 'exists':
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        result = db.fetchone('SELECT banned FROM users WHERE user_id = ?', (user_id,))
        if result:
            if isinstance(result, dict):
                return int(result.get('banned', 0))
            else:
                return int(result[0]) if result[0] else 0
    return 0


def checkUserExistsUsername(username):
    """Проверяет существование пользователя по username"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchone('SELECT * FROM users WHERE fullName = ?', (username,))
    if info is None:
        return 'empty', 'empty', 'empty', 'empty'
    else:
        if isinstance(info, dict):
            user_id = info.get('user_id', 'empty')
            pay_status = info.get('pay_status', 'empty')
            rank = info.get('rank', 'empty')
        else:
            user_id = info[0] if len(info) > 0 else 'empty'
            pay_status = info[1] if len(info) > 1 else 'empty'
            rank = info[3] if len(info) > 3 else 'empty'
        return user_id, pay_status, rank, username


def regUser(user_id, username):
    """Регистрирует нового пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    try:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        db.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (user_id, 0, 0, 0, 0, username, 0, 0, 0,))
        sendLogToAdm(
            f'<i>Новый юзер в боте:</i> @{username} | <code>{user_id}</code>')
    except Exception as e:
        logger_bot.error('SQL ERROR ' + str(e))


def changeSomeUserParam(user_id, param, paramNew):
    """Изменяет параметр пользователя (осторожно с SQL injection!)"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    # ВАЖНО: param не должен быть пользовательским вводом, только предопределенные значения
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    db.execute(f'UPDATE users SET {param} = ? WHERE user_id = ?', (paramNew, user_id,))


def changeUsername(user_id, username):
    """Изменяет username пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    db.execute('UPDATE users SET full_name_payments = ? WHERE user_id = ?', (username, user_id,))


def banUser(user_id):
    """Блокирует пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    db.execute('UPDATE users SET banned = 1 WHERE user_id = ?', (user_id,))


def unbanUser(user_id):
    """Разблокирует пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    db.execute('UPDATE users SET banned = 0 WHERE user_id = ?', (user_id,))


def changeUserAdminLink(user_id, status, string):
    """Изменяет статус админа пользователя и обновляет ссылку"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    db.execute('UPDATE users SET rank = ? WHERE user_id = ?', (status, user_id,))
    db.execute('UPDATE admin SET activated = 1')
    db.execute('UPDATE admin SET link_id = ?', (string,))
    db.execute('UPDATE admin SET activated = 0')


def takeUserSub(user_id):
    """Отменяет подписку пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    db.execute('UPDATE users SET pay_status = 0 WHERE user_id = ?', (user_id,))
    db.execute('UPDATE users SET last_pay = 0 WHERE user_id = ?', (user_id,))
    db.execute('UPDATE users SET end_pay = 0 WHERE user_id = ?', (user_id,))


def changeUserAdmin(user_id):
    """Переключает статус админа пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    now = checkUserAdmin(user_id)
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    if now == 'admin':
        db.execute('UPDATE users SET rank = 0 WHERE user_id = ?', (user_id,))
        return 'usered'
    else:
        db.execute('UPDATE users SET rank = 1 WHERE user_id = ?', (user_id,))
        return 'admined'


def createRieltor(rieltor_id, fullname, phone, email, photo):
    """Создает запись о риелторе"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    try:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        db.execute("INSERT INTO rieltors VALUES (?, ?, ?, ?, ?)",
                   (rieltor_id, fullname, email, photo, phone,))
    except Exception as e:
        logger_bot.error('SQL ERROR ' + str(e))


def createEvent(event_id, desc, date, title, link, name, photo):
    """Создает запись о событии"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    try:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        db.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (event_id, desc, date, title, link, name, photo,))
    except Exception as e:
        logger_bot.error('SQL ERROR ' + str(e))


def createContact(contact_id, fullname, phone, email, photo, job):
    """Создает запись о контакте"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    try:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        db.execute("INSERT INTO contacts VALUES (?, ?, ?, ?, ?, ?)",
                   (contact_id, fullname, email, photo, phone, job,))
    except Exception as e:
        logger_bot.error('SQL ERROR ' + str(e))


def createMeeting(user_id, day, meeting_id, roomnum):
    """Создает запись о встрече"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    try:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        db.execute("INSERT INTO meetings VALUES (?, ?, ?, ?, ?, ?)",
                   (meeting_id, user_id, 0, day, 'None', int(roomnum)))
    except Exception as e:
        logger_bot.error('SQL ERROR ' + str(e))


def checkRoom(meeting_id):
    """Получает номер комнаты для встречи"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    result = db.fetchone('SELECT roomnum FROM meetings WHERE meeting_id = ?', (meeting_id,))
    if result:
        if isinstance(result, dict):
            return str(result.get('roomnum', ''))
        else:
            return str(result[0]) if result[0] else ''
    return ''


def checkmeetingid(user_id, date, roomnum, time):
    """Проверяет существование встречи по параметрам"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    result = db.fetchone(
        'SELECT meeting_id FROM meetings WHERE user_id = ? AND roomnum = ? AND date = ? AND times LIKE ?',
        (user_id, roomnum, date, f'%{time}%'))
    if result:
        if isinstance(result, dict):
            return result.get('meeting_id', '')
        else:
            return result[0] if result[0] else ''
    return ''


def checkTimes(meeting_id):
    """Получает времена встречи"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    result = db.fetchone('SELECT times FROM meetings WHERE meeting_id = ?', (meeting_id,))
    if result:
        if isinstance(result, dict):
            info = str(result.get('times', 'None'))
        else:
            info = str(result[0]) if result[0] else 'None'
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
    return 'Empty'


def editTimes(meeting_id, time, roomnum):
    """Редактирует времена встречи"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    now_time = checkTimes(meeting_id)
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    if time not in now_time:
        if now_time == 'Empty':
            date = str(checkMeetingDay(meeting_id, roomnum))
            info = checkTimeExists(time, date, roomnum)
            try:
                print(info[0])
                return 'busied'
            except:
                db.execute('UPDATE meetings SET times = ? WHERE meeting_id = ? AND roomnum = ?', (time, meeting_id, roomnum))
        else:
            date = str(checkMeetingDay(meeting_id, roomnum))
            info = checkTimeExists(time, date, roomnum)
            try:
                print(info[0])
                return 'busied'
            except:
                finish = now_time + time
                db.execute('UPDATE meetings SET times = ? WHERE meeting_id = ? AND roomnum = ?', (finish, meeting_id, roomnum))
    else:
        now_time = now_time.split(';')
        now_time.remove(time.replace(';', ''))
        full_data = ';'.join(now_time)
        if full_data == '':
            full_data = 'None'
        db.execute('UPDATE meetings SET times = ? WHERE meeting_id = ? AND roomnum = ?', (str(full_data), meeting_id, roomnum))


def checkMeetingDay(meeting_id, roomnum):
    """Получает дату встречи"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    result = db.fetchone("SELECT date FROM meetings WHERE meeting_id = ? AND roomnum = ?", (meeting_id, roomnum))
    if result:
        if isinstance(result, dict):
            return result.get('date', '')
        else:
            return result[0] if result[0] else ''
    return ''


def deleteMeeting(meeting_id):
    """Удаляет встречу"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    try:
        meeting_id = str(meeting_id)
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        db.execute("DELETE FROM meetings WHERE meeting_id = ?", (meeting_id,))
        return True  # Успешное удаление
    except Exception as e:
        logger_bot.error(f"Ошибка при удалении встречи: {e}")
        return False  # Ошибка при удалении


def getRieltorId(id):
    """Получает данные риелтора по ID"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchone('SELECT * FROM rieltors WHERE id = ?', (id,))
    return info


def getEventId(id):
    """Получает данные события по ID"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchone('SELECT * FROM events WHERE event_id = ?', (id,))
    return info


def getContactId(id):
    """Получает данные контакта по ID"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchone('SELECT * FROM contacts WHERE id = ?', (id,))
    return info


def getUserById(id):
    """Получает fullname пользователя по ID"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    result = db.fetchone('SELECT fullname FROM users WHERE user_id = ?', (id,))
    if result:
        if isinstance(result, dict):
            return result.get('fullname', '')
        else:
            return result[0] if result[0] else ''
    return ''


def checkTimeExists(time, day, roomnum):
    """Проверяет, занято ли время"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchall("SELECT times FROM meetings WHERE date = ? AND times LIKE ? AND roomnum = ?", (day, f'%{time}%', roomnum))
    return info


def checkTimeExists1(day, roomnum):
    """Проверяет занятые времена и возвращает словарь {время: имя_пользователя}"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    
    # Получаем все занятые времена и соответствующие user_id
    time_user_pairs = db.fetchall("SELECT times, user_id FROM meetings WHERE date = ? AND roomnum = ?", (day, roomnum))

    # Создаем словарь {время: имя_пользователя}
    occupied_times = {}
    for pair in time_user_pairs:
        if isinstance(pair, dict):
            time_slots = pair.get('times', '')
            user_id = pair.get('user_id', '')
        else:
            time_slots = pair[0] if len(pair) > 0 else ''
            user_id = pair[1] if len(pair) > 1 else ''
        
        if not time_slots:
            continue

        # Получаем имя пользователя
        user_result = db.fetchone("SELECT full_name FROM users WHERE user_id = ?", (user_id,))
        if user_result:
            if isinstance(user_result, dict):
                user_name = user_result.get('full_name', 'Неизвестный пользователь')
            else:
                user_name = user_result[0] if user_result[0] else "Неизвестный пользователь"
        else:
            user_name = "Неизвестный пользователь"

        # Разбиваем по `;` и сохраняем каждое время отдельно
        for slot in time_slots.split(';'):
            cleaned_slot = slot.strip()
            if cleaned_slot:  # Игнорируем пустые строки
                occupied_times[cleaned_slot] = user_name

    return occupied_times


def getAllMeetings():
    """Получает все встречи"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    rows = db.fetchall("SELECT * FROM meetings")
    return rows


def makeMeetCompleted(meeting_id, username, roomnum):
    """Отмечает встречу как завершенную"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    day = str(checkMeetingDay(meeting_id, roomnum))
    times = checkTimes(meeting_id).split(';')
    full_data = ' '.join(times)
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    db.execute('UPDATE meetings SET status = 1 WHERE meeting_id = ? AND roomnum = ?', (meeting_id, roomnum))
    # sendLogToAdm(f'Пользователь @{username} забронировал переговорную на {day} на время: {full_data}')
#    users = getAllUsersForAd()
#    for i in users:
#        res = sendLogToUser(f'Пользователь @{username} забронировал переговорную на {day} на время: {full_data}', i[0])


def getRieltors():
    """Получает список всех риелторов"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchall("SELECT * FROM rieltors ORDER BY full_name")
    return info


def getEvents():
    """Получает список всех событий, отсортированных по дате"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchall("SELECT * FROM events ORDER BY date ASC")
    return info


def getContacts():
    """Получает список всех контактов"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchall("SELECT * FROM contacts")
    return info


def getUserPay(user_id):
    """Получает статус оплаты пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    result = db.fetchone("SELECT pay_status FROM users WHERE user_id = ?", (user_id,))
    if result:
        if isinstance(result, dict):
            return int(result.get('pay_status', 0))
        else:
            return int(result[0]) if result[0] else 0
    return 0


def getPayment(id):
    """Получает информацию о платеже"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchone("SELECT * FROM payments WHERE payment_id = ?", (id,))
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


def getPaidUsersCount():
    """Получает количество оплативших пользователей"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main")
    result = db.fetchone("SELECT COUNT(*) FROM users WHERE pay_status = 1")
    if result:
        if isinstance(result, dict):
            return int(list(result.values())[0])
        else:
            return int(result[0]) if result[0] else 0
    return 0


def getPaidUsers():
    """Получает список оплативших пользователей"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main")
    info = db.fetchall("SELECT full_name FROM users WHERE pay_status::int = 1")
    return info


def getPaidUsersForAd():
    """Получает список ID оплативших пользователей для админов"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchall("SELECT user_id FROM users WHERE pay_status::int = 1")
    return info


def getFreeUsersForAd():
    """Получает список ID неоплативших пользователей для админов"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchall("SELECT user_id FROM users WHERE pay_status::int = 0")
    return info


def delRietlor(rieltor_id):
    """Удаляет риелтора"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    db.execute("DELETE FROM rieltors WHERE id = ?", (rieltor_id,))


def delContact(contact_id):
    """Удаляет контакт"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    db.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))


def delEvent(event_id):
    """Удаляет событие"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    db.execute("DELETE FROM events WHERE event_id = ?", (event_id,))


def getAllUsersForAd():
    """Получает список всех ID пользователей для админов"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchall("SELECT user_id FROM users")
    return info


def getAllUsersForApi():
    """Получает всех пользователей для API"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchall("SELECT * FROM users")
    return info


def getAllPaymentsForApi():
    """Получает все платежи для API, отсортированные по времени"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchall("SELECT * FROM payments ORDER BY ts DESC")
    return info


def getFreeUsersCount():
    """Получает количество неоплативших пользователей"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main")
    result = db.fetchone("SELECT COUNT(*) FROM users WHERE pay_status::int = 0")
    if result:
        if isinstance(result, dict):
            return int(list(result.values())[0])
        else:
            return int(result[0]) if result[0] else 0
    return 0


def getUsersCount():
    """Получает общее количество пользователей"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main")
    result = db.fetchone("SELECT COUNT(*) FROM users")
    if result:
        if isinstance(result, dict):
            return int(list(result.values())[0])
        else:
            return int(result[0]) if result[0] else 0
    return 0


def getPaymentCount():
    """Получает общее количество платежей"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main")
    result = db.fetchone("SELECT COUNT(*) FROM payments")
    if result:
        if isinstance(result, dict):
            return int(list(result.values())[0])
        else:
            return int(result[0]) if result[0] else 0
    return 0


def getUserRef(user_id):
    """Получает ID реферера пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    info = db.fetchone("SELECT reffer_id FROM refferal WHERE user_id = ?", (user_id,))
    if info is not None:
        if isinstance(info, dict):
            reffer_id = int(info.get('reffer_id', 0))
        else:
            reffer_id = int(info[0]) if info[0] else 0
        return reffer_id
    else:
        return '404'


def giveUserSub(user_id, months):
    """Дает пользователю подписку на указанное количество месяцев"""
    from bot.tgbot.databases.database import DatabaseConnection
    
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
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
    db.execute('UPDATE users SET last_pay = ? WHERE user_id = ?', (now_ts, user_id,))
    db.execute('UPDATE users SET end_pay = ? WHERE user_id = ?', (timestamp2, user_id,))
    db.execute('UPDATE users SET pay_status = 1 WHERE user_id = ?', (user_id,))


def makePaymentCompleted(id):
    """Отмечает платеж как завершенный и обновляет подписку пользователя"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    user_id, amount, created, status = getPayment(id)
    db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
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
        db.execute('UPDATE payments SET status = 1 WHERE payment_id = ?', (id,))
        db.execute('UPDATE users SET last_pay = ? WHERE user_id = ?', (now_ts, user_id,))
        db.execute('UPDATE users SET end_pay = ? WHERE user_id = ?', (timestamp2, user_id,))
        db.execute('UPDATE users SET pay_status = 1 WHERE user_id = ?', (user_id,))
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
            db.execute('UPDATE users SET end_pay = ? WHERE user_id = ?', (timestamp, ref,))
            sendLogToUser(
                f'Ваш рефферал с ID {user_id} купил подписку, к вашей подписке добавлен 1 месяц.', ref)


def createPayment(id, amount, user_id):
    """Создает запись о платеже"""
    from bot.tgbot.databases.database import DatabaseConnection
    
    now_ts = int(time.time())
    try:
        db = DatabaseConnection(MAIN_DB_PATH, schema="main" if DB_TYPE == "postgres" else None)
        db.execute("INSERT INTO payments VALUES (?, ?, ?, ?, 0)", (user_id, id, amount, now_ts,))
    except Exception as e:
        logger_bot.error('SQL ERROR ' + str(e))
