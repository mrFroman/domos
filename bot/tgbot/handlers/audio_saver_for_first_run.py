# import os
# import asyncio
# import platform

# import telethon
# from pathlib import Path
# from telethon import TelegramClient, types
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker

# from tgbot.models.audio_saver_models import Base, AudioFile
# from tgbot.services.speech_yandex import process_voice_with_yandex_telethon
# from tgbot.services.speech_faster_whisper import process_voice_with_faster_whisper


# # Конфиг
# API_ID = os.getenv("TELEGRAM_API_ID", "")
# API_HASH = os.getenv("TELEGRAM_API_HASH", "")
# SESSION_NAME = "audio_saver_session"
# CHANNEL_ID = int(os.getenv("PAID_CHANNEL", ""))  # твой канал

# BASE_DIR = Path(__file__).parent.parent
# SAVE_DIR = "downloaded_audio"
# os.makedirs(SAVE_DIR, exist_ok=True)

# # Настройка БД
# DB_PATH = os.path.join(BASE_DIR, "databases", "downloaded_audio.db")
# engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
# Base.metadata.create_all(engine)
# SessionLocal = sessionmaker(bind=engine)

# system_version = platform.uname().release
# device_model = platform.uname().machine
# app_version = telethon.version.__version__


# async def main():
#     client = TelegramClient(
#         SESSION_NAME,
#         int(API_ID),
#         API_HASH,
#         system_version=system_version,
#         device_model=device_model,
#         app_version=app_version
#     )
#     await client.start()

#     session = SessionLocal()
#     try:
#         async for message in client.iter_messages(CHANNEL_ID, limit=None):
#             print(f"Обрабатываем сообщение {message.id}, типы медиа: {message.media}")
#             if not message.media:
#                 continue

#             doc = getattr(message.media, 'document', None)
#             if not doc:
#                 continue

#             # Проверяем аудио через DocumentAttributeAudio
#             audio_attr = next((a for a in doc.attributes if isinstance(a, types.DocumentAttributeAudio)), None)
#             if not audio_attr:
#                 continue

#             # Имя файла из DocumentAttributeFilename или генерируем
#             file_name_attr = next((a.file_name for a in doc.attributes if isinstance(a, types.DocumentAttributeFilename)), None)
#             file_name = file_name_attr or f"{doc.id}.ogg"
#             local_path = os.path.join(SAVE_DIR, file_name)

#             # Скачиваем файл локально (если нужно сохранить копию)
#             await client.download_media(message, file=local_path)
#             print(f"Скачали файл {local_path}")

#             # Распознаём текст через новую функцию
#             audio_text = await process_voice_with_faster_whisper(local_path)
#             print(f"Распознали текст {audio_text[-100:]}")

#             doc = message.media.document  # это объект Document

#             file_id = doc.id
#             file_unique_id = f"{doc.id}_{doc.access_hash}"  # уникальный идентификатор
             
#             existing = session.query(AudioFile).filter_by(file_unique_id=str(doc.id)).first()
#             if existing:
#                 print(f"Файл {file_name} уже есть в БД, пропускаем")
#                 continue

#             # Сохраняем в БД
#             audio_entry = AudioFile(
#                 file_id=str(file_id),
#                 file_unique_id=str(file_unique_id),
#                 file_name=file_name or f"{file_unique_id}.mp3",
#                 file_path=local_path,
#                 audio_text=audio_text if audio_text else "Текст не распознан",
#                 message_id=message.id,
#                 channel_id=CHANNEL_ID
#             )
#             session.add(audio_entry)
#             session.commit()
#             print(f"Сохранено: {file_name} → {audio_text}")

#         await asyncio.sleep(1)

#     finally:
#         session.close()
#         await client.disconnect()


# if __name__ == "__main__":
#     asyncio.run(main())
