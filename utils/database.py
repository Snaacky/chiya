import logging
import os

import dataset

import constants

log = logging.getLogger(__name__)

def get_db():
    """ Returns the OS friendly path to the SQLite database. """
    return "".join(["sqlite:///", os.path.join(os.getcwd(), constants.Bot.database)])


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
    
    # Create mod_logs table and columns to store moderator actions.
    mod_notes = db.create_table("mod_notes")
    mod_notes.create_column("user_id", db.types.bigint)
    mod_notes.create_column("mod_id", db.types.bigint)
    mod_notes.create_column("timestamp", db.types.bigint)
    mod_notes.create_column("note", db.types.text)

    # Create remind_me table and columns to store remind_me messages.
    remind_me = db.create_table("remind_me")
    remind_me.create_column("reminder_location", db.types.integer)
    remind_me.create_column("author_id", db.types.integer)
    remind_me.create_column("date_to_remind", db.types.integer)
    remind_me.create_column("message", db.types.text)
    remind_me.create_column("sent", db.types.boolean, default=False)

    db.commit()
    # TODO: Retain what tables didn't exist/were created so we can print those to console.
    log.info("Created any missing tables and columns.")