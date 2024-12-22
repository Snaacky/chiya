import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ParentModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Bot(ParentModel):
    token: str
    prefix: str
    status: str
    log_level: str
    webhook_url: str


class Database(ParentModel):
    host: str
    user: str
    password: str
    database: str
    url: str


class Roles(ParentModel):
    staff: int
    trial: int


class Categories(ParentModel):
    tickets: int
    moderation: int
    logs: int
    development: int


class Channels(ParentModel):
    tickets: int
    questions: int
    moderation: int
    ticket_log: int
    nitro_log: int
    chiya_log: int


class Joyboard(ParentModel):
    joy_limit: int
    channel_id: int
    blacklisted: list[int]
    timeout: int


class Hl(ParentModel):
    timeout: int


class PrivateBin(ParentModel):
    url: str


class ChiyaConfig(ParentModel):
    guild_id: int
    bot: Bot
    database: Database
    roles: Roles
    categories: Categories
    channels: Channels
    joyboard: Joyboard
    hl: Hl
    privatebin: PrivateBin


workspace = Path(__file__).parent.parent
config_file = workspace / "config.toml"


if not config_file.is_file():
    raise FileNotFoundError("Unable to load config.yml, exiting...")

config = ChiyaConfig.model_validate(tomllib.load(config_file.open("rb")))
