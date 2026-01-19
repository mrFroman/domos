from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String, nullable=False)             # Telegram file_id
    file_unique_id = Column(String, nullable=False, unique=True)
    file_name = Column(String, nullable=True)            # Имя файла
    file_path = Column(String, nullable=False)            # Локальный путь
    message_id = Column(Integer, nullable=False)          # ID сообщения
    channel_id = Column(Integer, nullable=False)          # ID канала
    audio_text = Column(Text, nullable=True)              # Распознанный текст
    date_added = Column(DateTime, default=datetime.utcnow)
