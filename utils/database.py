import os

import dataset

import config


def get_db():
    """ Returns the OS friendly path to the SQLite database. """
    return "".join(["sqlite:///", os.path.join(os.getcwd(), config.DB_FILE)])


def setup_db():
    """ Sets up the tables needed for Chiya. """
    db = dataset.connect(get_db())
    # TODO: Add check to see if tables exists before creating.
    # Create mod_logs table and columns to store moderator actions.
    db.create_table("mod_logs")
    mod_logs = db.get_table("mod_logs")
    mod_logs.create_column("user_id", db.types.bigint)
    mod_logs.create_column("mod_id", db.types.bigint)
    mod_logs.create_column("timestamp", db.types.bigint)
    mod_logs.create_column("reason", db.types.text)
    mod_logs.create_column("type", db.types.text)
    
    # Create mod_logs table and columns to store moderator actions.
    db.create_table("mod_notes")
    mod_notes = db.get_table("mod_notes")
    mod_notes.create_column("user_id", db.types.bigint)
    mod_notes.create_column("mod_id", db.types.bigint)
    mod_notes.create_column("timestamp", db.types.bigint)
    mod_notes.create_column("note", db.types.text)
    db.commit()
    # TODO: Retain what tables didn't exist/were created so we can print those to console.
    print("Created tables and columns.")