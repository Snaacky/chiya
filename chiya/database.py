import dataset
from loguru import logger as log
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database

from config import config


class Database:
    def __init__(self) -> None:
        host = config["database"]["host"]
        database = config["database"]["database"]
        user = config["database"]["user"]
        password = config["database"]["password"]

        if not all([host, database, user, password]):
            log.error("One or more database connection variables are missing, exiting...")
            raise SystemExit

        self.url = f"mysql://{user}:{password}@{host}/{database}?charset=utf8mb4"

    def get(self) -> dataset.Database:
        """Returns the dataset database object."""
        return dataset.connect(url=self.url)

    def setup(self) -> None:
        """Sets up the tables needed for Chiya."""
        engine = create_engine(self.url)
        if not database_exists(engine.url):
            create_database(engine.url)

        db = self.get()

        if "mod_logs" not in db:
            mod_logs = db.create_table("mod_logs")
            mod_logs.create_column("user_id", db.types.bigint)
            mod_logs.create_column("mod_id", db.types.bigint)
            mod_logs.create_column("timestamp", db.types.bigint)
            mod_logs.create_column("reason", db.types.text)
            mod_logs.create_column("duration", db.types.text)
            mod_logs.create_column("type", db.types.text)
            log.info("Created missing table: mod_logs")

        if "remind_me" not in db:
            remind_me = db.create_table("remind_me")
            remind_me.create_column("reminder_location", db.types.bigint)
            remind_me.create_column("author_id", db.types.bigint)
            remind_me.create_column("date_to_remind", db.types.bigint)
            remind_me.create_column("message", db.types.text)
            remind_me.create_column("sent", db.types.boolean, default=False)
            log.info("Created missing table: remind_me")

        if "timed_mod_actions" not in db:
            timed_mod_actions = db.create_table("timed_mod_actions")
            timed_mod_actions.create_column("user_id", db.types.bigint)
            timed_mod_actions.create_column("mod_id", db.types.bigint)
            timed_mod_actions.create_column("action_type", db.types.text)
            timed_mod_actions.create_column("start_time", db.types.bigint)
            timed_mod_actions.create_column("end_time", db.types.bigint)
            timed_mod_actions.create_column("is_done", db.types.boolean, default=False)
            timed_mod_actions.create_column("reason", db.types.text)
            log.info("Created missing table: timed_mod_actions")

        if "tickets" not in db:
            tickets = db.create_table("tickets")
            tickets.create_column("user_id", db.types.bigint)
            tickets.create_column("guild", db.types.bigint)
            tickets.create_column("timestamp", db.types.bigint)
            tickets.create_column("ticket_subject", db.types.text)
            tickets.create_column("ticket_message", db.types.text)
            tickets.create_column("log_url", db.types.text)
            tickets.create_column("status", db.types.boolean)
            log.info("Created missing table: tickets")

        if "starboard" not in db:
            starboard = db.create_table("starboard")
            starboard.create_column("channel_id", db.types.bigint)
            starboard.create_column("message_id", db.types.bigint)
            starboard.create_column("star_embed_id", db.types.bigint)
            log.info("Created missing table: starboard")

        if "joyboard" not in db:
            joyboard = db.create_table("joyboard")
            joyboard.create_column("channel_id", db.types.bigint)
            joyboard.create_column("message_id", db.types.bigint)
            joyboard.create_column("joy_embed_id", db.types.bigint)
            log.info("Created missing table: joyboard")

        if "highlights" not in db:
            highlights = db.create_table("highlights")
            highlights.create_column("term", db.types.text)
            highlights.create_column("users", db.types.text)
            log.info("Created missing table: highlights")

        # utf8mb4_unicode_ci is required to support emojis and other unicode.
        # dataset does not expose collation in any capacity so rather than
        # checking an object property, we have to do this hacky way of checking
        # the charset via queries and updating it where necessary.
        for table in db.tables:
            charset = next(db.query(f"SHOW TABLE STATUS WHERE NAME = '{table}';"))["Collation"]
            if charset == "utf8mb4_unicode_ci":
                continue
            db.query(f"ALTER TABLE {table} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            log.info(f"Converted table to utf8mb4_unicode_ci: {table}")

        db.commit()
        db.close()
