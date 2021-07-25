import logging
import os

import dataset

log = logging.getLogger(__name__)

def get_db():
    """ Returns the OS friendly path to the SQLite database. """
    HOST = os.getenv("MYSQL_HOST")
    DATABASE = os.getenv("MYSQL_DATABASE")
    USER = os.getenv("MYSQL_USER")
    PASSWORD = os.getenv("MYSQL_PASSWORD")
   
    return f"mysql://{USER}:{PASSWORD}@{HOST}/{DATABASE}"

def setup_db():
    """ Sets up the tables needed for Chiya. """
    db = dataset.connect(get_db())
    # TODO: Add check to see if tables exists before creating.
    # Create mod_logs table and columns to store moderator actions.
    mod_logs = db.create_table("mod_logs")
    mod_logs.create_column("user_id", db.types.bigint)
    mod_logs.create_column("mod_id", db.types.bigint)
    mod_logs.create_column("timestamp", db.types.bigint)
    mod_logs.create_column("reason", db.types.text)
    mod_logs.create_column("type", db.types.text)

    # Create remind_me table and columns to store remind_me messages.
    remind_me = db.create_table("remind_me")
    remind_me.create_column("reminder_location", db.types.integer)
    remind_me.create_column("author_id", db.types.integer)
    remind_me.create_column("date_to_remind", db.types.integer)
    remind_me.create_column("message", db.types.text)
    remind_me.create_column("sent", db.types.boolean, default=False)

    # create timed_mod_actions table and columns to store timed moderator actions.
    timed_mod_actions = db.create_table("timed_mod_actions")
    timed_mod_actions.create_column("user_id", db.types.integer)
    timed_mod_actions.create_column("mod_id", db.types.integer)
    timed_mod_actions.create_column("action_type", db.types.text)
    timed_mod_actions.create_column("start_time", db.types.integer)
    timed_mod_actions.create_column("end_time", db.types.integer)
    timed_mod_actions.create_column("is_done", db.types.boolean, default=False)

    # create ticket table and columns to store the ticket status information
    tickets = db.create_table("tickets")
    tickets.create_column("user_id", db.types.integer)
    tickets.create_column("status", db.types.text)
    tickets.create_column("guild", db.types.bigint)
    tickets.create_column("timestamp", db.types.bigint)
    tickets.create_column("ticket_topic", db.types.text)
    tickets.create_column("log_url", db.types.text)

   
    db.commit()
    # TODO: Retain what tables didn't exist/were created so we can print those to console.
    log.info("Created any missing tables and columns.")