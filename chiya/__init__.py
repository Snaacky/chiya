import logging
import os
import sys
from logging import handlers
from pathlib import Path

import coloredlogs

from config import config


log_level = config["bot"]["log_level"]
if not log_level:
    log_level = "NOTSET"

# Logs format
format_string = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
log_format = logging.Formatter(format_string)

# Make a Log directory and file
log_file = Path("logs", "bot.log")
log_file.parent.mkdir(exist_ok=True)
file_handler = handlers.RotatingFileHandler(log_file, maxBytes=5242880, backupCount=7, encoding="utf8")
file_handler.setFormatter(log_format)

root_log = logging.getLogger()
root_log.setLevel(log_level)
root_log.addHandler(file_handler)

# making logs colorful and easy to read
if "COLOREDLOGS_LEVEL_STYLES" not in os.environ:
    coloredlogs.DEFAULT_LEVEL_STYLES = {
        **coloredlogs.DEFAULT_LEVEL_STYLES,
        "trace": {"color": 246},
        "critical": {"background": "red"},
        "debug": coloredlogs.DEFAULT_LEVEL_STYLES["info"],
    }

coloredlogs.DEFAULT_LOG_FORMAT = format_string
coloredlogs.DEFAULT_LOG_LEVEL = log_level
coloredlogs.install(logger=root_log, stream=sys.stdout, isatty=True)

# muffling "type" logs unless >= setLevel
if root_log.level != 0:
    if root_log.level < 20:
        # Getting tired of the heartbeat blocked warning when debugging.
        logging.getLogger("discord").setLevel(logging.ERROR)
    else:
        logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("chardet").setLevel(logging.WARNING)
    logging.getLogger("asyncprawcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger(__name__)
