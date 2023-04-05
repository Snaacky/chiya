import os

from loguru import logger as log
from pyaml_env import parse_config


path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yml")
if not os.path.isfile(path):
    log.error("Unable to load config.yml, exiting...")
    raise SystemExit

config = parse_config(path)
