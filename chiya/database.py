from sqlalchemy import Boolean, Column, ForeignKey, Integer, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, scoped_session, sessionmaker

from chiya.config import config

engine = create_engine(config.database.url, connect_args={"check_same_thread": False})
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


class Base:
    class QueryDescriptor:
        def __get__(self, instance, owner):
            return Session().query(owner)

    query = QueryDescriptor()

    def save(self):
        "Save the current instance to the database."
        session = Session()
        try:
            session.add(self)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

        return self


Base = declarative_base(cls=Base)


class ModLog(Base):
    __tablename__ = "mod_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    mod_id = Column(Integer, nullable=False)
    timestamp = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    duration = Column(Text, nullable=False)
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

    id = Column(Integer, primary_key=True)
    term = Column(Text, nullable=False)
    users = Column(Text, nullable=False)


class HighlightTerm(Base):
    __tablename__ = "highlight_terms"

    id = Column(Integer, primary_key=True)
    term = Column(Text, nullable=False, unique=True)
    users = relationship("HighlightUser", back_populates="term")


class HighlightUser(Base):
    __tablename__ = "highlight_users"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    term_id = Column(Integer, ForeignKey("highlight_terms.id"), nullable=False)
    term = relationship("HighlightTerm", back_populates="users")


Base.metadata.create_all(engine)
