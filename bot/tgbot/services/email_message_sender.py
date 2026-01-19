import smtplib
import os

# Добавляем необходимые подклассы - MIME-типы
import mimetypes
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


HOST_TURN = os.getenv('HOST_TURN', 'False').strip().lower() == 'true'

def send_email(msg_subj, msg_text, files):
    if HOST_TURN:
        addr_from = os.getenv('SENDER_EMAIL', '')                # Отправитель
        password = os.getenv('SENDER_PASSWORD', '')              # Пароль отправителя
        addr_to = os.getenv('LAWYER_EMAIL', '')                  # Получатель
    else:
        addr_from = os.getenv('TEST_SENDER_EMAIL', '')                # Отправитель
        password = os.getenv('TEST_SENDER_PASSWORD', '')              # Пароль отправителя
        addr_to = os.getenv('TEST_LAWYER_EMAIL', '')                  # Получатель

    msg = MIMEMultipart()                                    # Создаем сообщение
    msg['From'] = addr_from                                  # Адресат
    msg['To'] = addr_to                                      # Получатель
    msg['Subject'] = msg_subj                                # Тема сообщения

    body = msg_text                                          # Текст сообщения
    msg.attach(MIMEText(body, 'plain'))                      # Добавляем в сообщение текст

    process_attachement(msg, files)

    ''' ======== Этот блок настраивается для каждого почтового провайдера отдельно ================================'''
    context = ssl.create_default_context()
    server = smtplib.SMTP('smtp.bk.ru', 25)                  # Создаем объект SMTP
    server.starttls(context=context)                         # Начинаем шифрованный обмен по TLS
    # server.set_debuglevel(True)                            # Включаем режим отладки, если не нужен - можно закомментировать
    server.login(addr_from, password)                        # Получаем доступ
    server.send_message(msg)                                 # Отправляем сообщение
    server.quit()


def process_attachement(msg, files):                        # Функция по обработке списка, добавляемых к сообщению файлов
    for f in files:
        if os.path.isfile(f):                               # Если файл существует
            attach_file(msg,f)                              # Добавляем файл к сообщению
        elif os.path.exists(f):                             # Если путь не файл и существует, значит - папка
            dir = os.listdir(f)                             # Получаем список файлов в папке
            for file in dir:                                # Перебираем все файлы и...
                attach_file(msg,f+"/"+file)                 # ...добавляем каждый файл к сообщению


def attach_file(msg, filepath):                             # Функция по добавлению конкретного файла к сообщению
    filename = os.path.basename(filepath)                   # Получаем только имя файла
    ctype, encoding = mimetypes.guess_type(filepath)        # Определяем тип файла на основе его расширения
    if ctype is None or encoding is not None:               # Если тип файла не определяется
        ctype = 'application/octet-stream'                  # Будем использовать общий тип
    maintype, subtype = ctype.split('/', 1)                 # Получаем тип и подтип
    if maintype == 'text':                                  # Если текстовый файл
        with open(filepath) as fp:                          # Открываем файл для чтения
            file = MIMEText(fp.read(), _subtype=subtype)    # Используем тип MIMEText
            fp.close()                                      # После использования файл обязательно нужно закрыть
    elif maintype == 'image':                               # Если изображение
        with open(filepath, 'rb') as fp:
            file = MIMEImage(fp.read(), _subtype=subtype)
            fp.close()
    elif maintype == 'audio':                               # Если аудио
        with open(filepath, 'rb') as fp:
            file = MIMEAudio(fp.read(), _subtype=subtype)
            fp.close()
    else:                                                   # Неизвестный тип файла
        with open(filepath, 'rb') as fp:
            file = MIMEBase(maintype, subtype)              # Используем общий MIME-тип
            file.set_payload(fp.read())                     # Добавляем содержимое общего типа (полезную нагрузку)
            fp.close()
            encoders.encode_base64(file)                    # Содержимое должно кодироваться как Base64
    file.add_header('Content-Disposition', 'attachment', filename=filename)     # Добавляем заголовки
    msg.attach(file)                                        # Присоединяем файл к сообщению

