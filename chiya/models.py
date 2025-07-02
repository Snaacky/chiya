from typing import Self

from sqlalchemy import Boolean, Column, Integer, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, DeclarativeBase

from chiya.config import config

engine = create_engine(config.database.url, connect_args={"check_same_thread": False})
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


class Base(DeclarativeBase):
    __abstract__ = True

    query = Session.query_property()

    def save(self) -> Self:
        session = Session()
        session.add(self)
        session.commit()
        return self

    def delete(self) -> Self:
        session = Session()
        session.delete(self)
        session.commit()
        return self

    def flush(self) -> Self:
        session = Session()
        session.add(self)
        session.flush()
        return self


class ModLog(Base):
    __tablename__ = "mod_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    mod_id = Column(Integer, nullable=False)
    timestamp = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    duration = Column(Text, nullable=True)
    type = Column(Text, nullable=False)


class RemindMe(Base):
    __tablename__ = "remind_me"

    id = Column(Integer, primary_key=True)
    reminder_location = Column(Integer, nullable=False)
    author_id = Column(Integer, nullable=False)
    date_to_remind = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)
    sent = Column(Boolean, nullable=False, default=False)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    guild = Column(Integer, nullable=False)
    timestamp = Column(Integer, nullable=False)
    ticket_subject = Column(Text, nullable=False)
    ticket_message = Column(Text, nullable=False)
    log_url = Column(Text, nullable=False)
    status = Column(Boolean)


class Joyboard(Base):
    __tablename__ = "joyboard"

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, nullable=False)
    message_id = Column(Integer, nullable=False)
    joy_embed_id = Column(Integer, nullable=False)


class Highlight(Base):
    __tablename__ = "highlights"
    __table_args__ = (UniqueConstraint("term", "user_id", name="uq_user_term"),)

    id = Column(Integer, primary_key=True)
    term = Column(Text, nullable=False)
    user_id = Column(Integer, nullable=False)


Base.metadata.create_all(engine)
