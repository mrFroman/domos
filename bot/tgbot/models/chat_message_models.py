from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String, nullable=True)
    date = Column(DateTime, nullable=True)
    topic_name = Column(String, nullable=True)
    text = Column(String, nullable=True)

