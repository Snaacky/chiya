"""
Loads bot configuration from YAML files.

By default, this simply loads the default configuration located at `config-default.yml`.

If a file called `config.yml` is found in the project directory, the default configuration
is recursively updated with any settings from the custom configuration. Any settings left
out in the custom user configuration will stay their default values from `config-default.yml`.
"""

import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import List, Optional, Union

import yaml

log = logging.getLogger(__name__)


def _env_var_constructor(loader, node):
    """
    Implements a custom YAML tag for loading optional environment variables.

    If the environment variable is set, returns the value of it.

    Otherwise, returns `None`.

    Example usage in the YAML configuration:
        # Optional app configuration. Set `MY_APP_KEY` in the environment to use it.
        application:
            key: !ENV 'MY_APP_KEY'
    """

    default = None

    # Check if the node is a plain string value
    if node.id == 'scalar':
        value = loader.construct_scalar(node)
        key = str(value)
    else:
        # The node value is a list
        value = loader.construct_sequence(node)

        if len(value) >= 2:
            # If we have at least two values, then we have both a key and a default value
            default = value[1]
            key = value[0]
        else:
            # Otherwise, we just have a key
            key = value[0]

    return os.getenv(key, default)


def _join_var_constructor(loader, node):
    """ Implements a custom YAML tag for concatenating other tags in the document to strings.

    This allows for a much more DRY configuration file.
    """

    fields = loader.construct_sequence(node)
    return "".join(str(x) for x in fields)


yaml.SafeLoader.add_constructor("!ENV", _env_var_constructor)
yaml.SafeLoader.add_constructor("!JOIN", _join_var_constructor)


with open("config-default.yml", encoding="UTF-8") as file:
    _CONFIG_YAML = yaml.safe_load(file)


def _recursive_update(original, new):
    """
    Helper method which implements a recursive `dict.update` method, used for updating the
    original configuration with configuration specified by the user.
    """

    for key, value in original.items():
        if key not in new:
            continue

        if isinstance(value, Mapping):
            if not any(isinstance(subvalue, Mapping) for subvalue in value.values()):
                original[key].update(new[key])
            _recursive_update(original[key], new[key])
        else:
            original[key] = new[key]


if Path("config.yml").exists():
    # Overwriting default config with new config.
    print("INFO: Found `config.yml` file, loading constants from it.")
    with open("config.yml", encoding="UTF-8") as file:
        user_config = yaml.safe_load(file)
    _recursive_update(_CONFIG_YAML, user_config)


def check_required_keys(keys):
    """
    Verifies that keys that are set to be required are present in the
    loaded configuration.
    """
    for key_path in keys:
        lookup = _CONFIG_YAML
        try:
            for key in key_path.split('.'):
                lookup = lookup[key]
                if lookup is None:
                    raise KeyError(key)
        except KeyError:
            log.critical(
                f"A configuration for `{key_path}` is required, but was not found. "
                "Please set it in `config.yml` or setup an environment variable and try again."
                )
            # constants.py is loaded before logs, therefore, loggin in this file may not work properly.
            print(f"CRITICAL: A configuration for `{key_path}` is required, but was not found. "
                "Please set it in `config.yml` or setup an environment variable and try again.")
            raise


try:
    required_keys = _CONFIG_YAML['config']['required_keys']
except KeyError:
    pass
else:
    check_required_keys(required_keys)



class YAMLGetter(type):
    """
    Implements a custom metaclass used for accessing
    configuration data by simply accessing class attributes.

    Supports getting configuration from up to two levels
    of nested configuration through `section` and `subsection`.

    `section` specifies the YAML configuration section (or "key")
    in which the configuration lives, and must be set.

    `subsection` is an optional attribute specifying the section
    within the section from which configuration should be loaded.

    Example Usage:
    # config.yml
    bot:
        prefixes:
            direct_message: ''
            guild: '!'
    # config.py
    class Prefixes(metaclass=YAMLGetter):
        section = "bot"
        subsection = "prefixes"
    # Usage in Python code
    from config import Prefixes
    def get_prefix(bot, message):
        if isinstance(message.channel, PrivateChannel):
            return Prefixes.direct_message
        return Prefixes.guild
"""

    subsection = None

    def __getattr__(cls, name):
        name = name.lower()

        try:
            if cls.subsection is not None:
                return _CONFIG_YAML[cls.section][cls.subsection][name]
            return _CONFIG_YAML[cls.section][name]
        except KeyError:
            dotted_path = '.'.join(
                (cls.section, cls.subsection, name)
                if cls.subsection is not None else (cls.section, name)
            )
            log.critical(
                f"Tried accessing configuration variable at `{dotted_path}`, but it could not be found.")
            # constants.py is loaded before logs, therefore, loggin in this file may not work properly.
            print(
                f"CRITICAL: Tried accessing configuration variable at `{dotted_path}`, but it could not be found.")
            raise

    def __getitem__(cls, name):
        return cls.__getattr__(name)

    def __iter__(cls):
        """Return generator of key: value pairs of current constants class' config values."""
        for name in cls.__annotations__:
            yield name, getattr(cls, name)


# Dataclasses
class Bot(metaclass=YAMLGetter):
    """ Type hints of `config.yml` "bot". """
    section = "bot"

    prefix: str
    token: str
    log_level: Union[str, int]
    database: str


class Reddit(metaclass=YAMLGetter):
    section = "reddit"

    subreddit: Optional[str]
    client_id: Optional[str]
    client_secret: Optional[str]
    reddit_posts: Optional[int]
    poll_rate: Optional[int]
    user_agent: Optional[str]


class Colours(metaclass=YAMLGetter):
    section = "style"
    subsection = "colours"

    soft_red: int
    soft_green: int
    soft_orange: int
    soft_blue: int
    bright_green: int


class Emojis(metaclass=YAMLGetter):
    section = "style"
    subsection = "emojis"

    status_online: str
    status_offline: str
    status_idle: str
    status_dnd: str

    incident_actioned: str
    incident_unactioned: str
    incident_investigating: str

    bullet: str
    new: str
    pencil: str
    cross_mark: str
    check_mark: str


class Icons(metaclass=YAMLGetter):
    section = "style"
    subsection = "icons"

    crown_blurple: str
    crown_green: str
    crown_red: str

    defcon_denied: str  # noqa: E704
    defcon_disabled: str  # noqa: E704
    defcon_enabled: str  # noqa: E704
    defcon_updated: str  # noqa: E704

    filtering: str

    hash_blurple: str
    hash_green: str
    hash_red: str

    message_bulk_delete: str
    message_delete: str
    message_edit: str

    sign_in: str
    sign_out: str

    user_ban: str
    user_unban: str
    user_update: str

    user_mute: str
    user_unmute: str
    user_verified: str

    user_warn: str

    pencil: str

    remind_blurple: str
    remind_green: str
    remind_red: str

    questionmark: str

    voice_state_blue: str
    voice_state_green: str
    voice_state_red: str


class Guild(metaclass=YAMLGetter):
    section = "guild"

    id: int
    invite: str
    moderation_channels: List[int]
    submission_channels: List[int]
    staff_roles: List[int]


class Categories(metaclass=YAMLGetter):
    section = "guild"
    subsection = "categories"

    server: int
    community: int
    moderation: int
    development: int
    logs: int
    archive: int

class Channels(metaclass=YAMLGetter):
    section = "guild"
    subsection = "channels"

    rules: int
    announcements: int
    general: int
    shitposts: int
    bots: int
    art: int
    reddit_posts: int
    moderation: int
    commands: int
    votes: int
    chiya_dev: int
    bot_testing: int
    chiya_todo: int
    chiya_github: int
    index_dev: int
    index_editors: int
    index_todo: int
    index_github: int
    wiki_github: int
    joins_leaves: int
    development: int
    tools_guides: int
    wallpapers: int
    

class Roles(metaclass=YAMLGetter):
    section = "guild"
    subsection = "roles"

    perverts: int
    admin: int
    staff: int
    discord_mod: int
    reddit_mod: int
    developer: int
    booster: int


# Paths
BOT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(BOT_DIR, os.pardir))
