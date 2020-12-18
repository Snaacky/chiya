import logging

import config

# setting the global log level
logging.basicConfig(level=config.) # can only be configured once

# muffling "type" logs unless >= setLevel
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("chardet").setLevel(logging.WARNING)
#logging.getLogger("prawcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger(__name__)