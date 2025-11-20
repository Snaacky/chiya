from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ModLog(Base):
    __tablename__ = "mod_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    mod_id: Mapped[int]
    timestamp: Mapped[int]
    reason: Mapped[str | None]
    duration: Mapped[str | None]
    type: Mapped[str]


class RemindMe(Base):
    __tablename__ = "remind_me"

    id: Mapped[int] = mapped_column(primary_key=True)
    reminder_location: Mapped[int]
    author_id: Mapped[int]
    date_to_remind: Mapped[int]
    message: Mapped[str]
    sent: Mapped[bool] = mapped_column(default=False)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    guild: Mapped[int]
    timestamp: Mapped[int]
    ticket_subject: Mapped[int]
    ticket_message: Mapped[int]
    log_url: Mapped[str | None]
    status: Mapped[bool]


class Joyboard(Base):
    __tablename__ = "joyboard"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int]
    message_id: Mapped[int]
    joy_embed_id: Mapped[int]


class Highlight(Base):
    __tablename__ = "highlights"

    id: Mapped[int] = mapped_column(primary_key=True)
    term: Mapped[str]
    users: Mapped[list[int]] = mapped_column(JSON)
