from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from chiya.config import config
from chiya.models import Base


engine = create_engine(config.database.url, connect_args={"check_same_thread": False})
factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
session = scoped_session(factory)

Base.metadata.create_all(engine)
