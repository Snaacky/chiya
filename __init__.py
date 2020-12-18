import logging
from logging import Logger, handlers

import config


TRACE_LEVEL = logging.TRACE = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")

# Adding Trace to enchance debugging verbose logs. DO NOT USE FOR PRODUCTION
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

# setting the global log level
logging.basicConfig(level=config.LOGLEVEL) # can only be configured once

# muffling "type" logs unless >= setLevel
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("chardet").setLevel(logging.WARNING)
#logging.getLogger("prawcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger(__name__)