import logging
import os

import yaml

log = logging.getLogger(__name__)

if not os.getenv("CONFIG") or not os.path.isfile(os.getenv("CONFIG")):
    log.error("Unable to load config.yml, exiting...")
    raise SystemExit

with open(os.getenv("CONFIG"), "r") as f:
    config = yaml.safe_load(f)
