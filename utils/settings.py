import logging
import os
import sys

import yaml

log = logging.getLogger(__name__)

if not os.getenv("SETTINGS"):
    log.error("Unable to find settings.yml, exiting...")
    sys.exit()

with open(os.getenv("SETTINGS"), "r") as f:
    settings = yaml.safe_load(f)
