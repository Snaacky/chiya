from typing import Annotated, Self, TypeAlias

from sqlalchemy import UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, scoped_session, sessionmaker

from chiya.config import config

engine = create_engine(config.database.url, connect_args={"check_same_thread": False})
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


PrimaryIntKey: TypeAlias = Annotated[int, mapped_column(primary_key=True)]


class Base(MappedAsDataclass, DeclarativeBase):
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

    id: Mapped[PrimaryIntKey] = mapped_column(init=False)
    user_id: Mapped[int]
    mod_id: Mapped[int]
    timestamp: Mapped[int]
    reason: Mapped[str]
    duration: Mapped[str | None]
    type: Mapped[str]


class RemindMe(Base):
    __tablename__ = "remind_me"

    id: Mapped[PrimaryIntKey] = mapped_column(init=False)
    reminder_location: Mapped[int]
    author_id: Mapped[int]
    date_to_remind: Mapped[int]
    message: Mapped[str]
    sent: Mapped[bool] = mapped_column(default=False)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[PrimaryIntKey] = mapped_column(init=False)
    user_id: Mapped[int]
    guild: Mapped[int]
    timestamp: Mapped[int]
    ticket_subject: Mapped[str]
    ticket_message: Mapped[str]
    log_url: Mapped[str]
    status: Mapped[bool]


class Joyboard(Base):
    __tablename__ = "joyboard"

    id: Mapped[PrimaryIntKey] = mapped_column(init=False)
    channel_id: Mapped[int]
    message_id: Mapped[int]
    joy_embed_id: Mapped[int]


class Highlight(Base):
    __tablename__ = "highlights"
    __table_args__ = (UniqueConstraint("term", "user_id", name="uq_user_term"),)

    id: Mapped[PrimaryIntKey] = mapped_column(init=False)
    term: Mapped[str]
    user_id: Mapped[int]


Base.metadata.create_all(engine)
