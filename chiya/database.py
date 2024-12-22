from sqlalchemy import create_engine, BigInteger, Boolean, Column, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from chiya.config import config


Base = declarative_base()
engine = create_engine(config.database.url, connect_args={"check_same_thread": False})
session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class BaseModel(Base):
    __abstract__ = True

    def save(self):
        session.add(self)
        session.commit()
        return self

    def delete(self):
        session.delete(self)
        session.commit()
        return self

    def flush(self):
        session.add(self)
        session.flush()
        return self


class ModLog(Base):
    __tablename__ = "mod_logs"

    id = Column(Integer, primar_key=True)
    user_id = Column(BigInteger, nullable=False)
    mod_id = Column(BigInteger, nullable=False)
    timestamp = Column(BigInteger, nullable=False)
    reason = Column(Text, nullable=False)
    duration = Column(Text, nullable=False)
    type = Column(Text, nullable=False)


class RemindMe(Base):
    __tablename__ = "remind_me"

    id = Column(Integer, primar_key=True)
    reminder_location = Column(BigInteger, nullable=False)
    author_id = Column(BigInteger, nullable=False)
    date_to_remind = Column(BigInteger, nullable=False)
    message = Column(Text, nullable=False)
    sent = Column(Boolean, nullable=False, default=False)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    guild = Column(BigInteger, nullable=False)
    timestamp = Column(BigInteger, nullable=False)
    ticket_subject = Column(Text, nullable=False)
    ticket_message = Column(Text, nullable=False)
    log_url = Column(Text, nullable=False)
    status = Column(Boolean)


class Joyboard(Base):
    __tablename__ = "joyboard"

    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    joy_embed_id = Column(BigInteger, nullable=False)


class Highlight(Base):
    __tablename__ = "highlights"

    id = Column(Integer, primary_key=True)
    term = Column(Text, nullable=False)
    users = Column(Text, nullable=False)
