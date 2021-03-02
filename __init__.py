import logging
import os
import sys
from logging import Logger, handlers
from pathlib import Path

import coloredlogs

import constants


log_level = constants.Bot.log_level

if log_level is None:
    log_level = "NOTSET"

# Adding Trace to enchance debugging verbose logs. DO NOT USE FOR PRODUCTION

TRACE_LEVEL = logging.TRACE = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


def monkeypatch_trace(self: logging.Logger, msg: str, *args, **kwargs) -> None:
    """
    Log 'msg % args' with severity 'TRACE'.\n
    To pass exception information, use the keyword argument exc_info with a true value, e.g.\n
    logger.trace("Houston, we have an %s", "interesting problem", exc_info=1)\n
    """
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, msg, args, **kwargs)


# Initializing Trace
Logger.trace = monkeypatch_trace

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
        "debug": coloredlogs.DEFAULT_LEVEL_STYLES["info"]
    }

coloredlogs.DEFAULT_LOG_FORMAT = format_string
coloredlogs.DEFAULT_LOG_LEVEL = log_level
coloredlogs.install(logger=root_log, stream=sys.stdout)

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