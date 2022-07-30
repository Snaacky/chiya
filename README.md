<p align="center">
<img width="150" height="150" src="https://i.imgur.com/Lkqobis.png">
</p>

<p align="center">
<b>A moderation-heavy general purpose Discord bot.</b>
</p>

<p align="center">
<a href="https://discord.gg/snackbox"><img src="https://img.shields.io/discord/974468300304171038?label=Discord&logo=discord"></a> <a href="https://github.com/snaacky/chiya/actions"><img src="https://github.com/snaacky/chiya/workflows/Docker/badge.svg?branch=master"></a>
</p>

## Getting started

Chiya is deployed into a production environment using [Docker](https://docs.docker.com/engine/reference/run/) images. As such, the install guide will focus on deployment via Docker. Chiya has been tested on both Windows and Linux bare metal environments and attempts to retain compatibility across both operating systems but this may not always be the case. The install guide assumes that you already have Docker and [docker-compose](https://docs.docker.com/compose/) installed.

You will also need a Discord bot with [privileged intents](https://discordpy.readthedocs.io/en/stable/intents.html) enabled and the token for that bot before installation. You can create a new Discord bot [here](https://discord.com/developers/). Keep in mind Chiya will need the `bot` and `applications.commands` scopes selected when you generate your OAuth2 URL to function properly. If you intend on using the Reddit functionality, you will also need to create a Reddit application [here](https://www.reddit.com/prefs/apps/).

## Install

**Step 1:** Download the `docker-compose.yml` to your local file system.

**Step 2:** Create a `.env` file in the same folder and fill out the following:

```env
# The bot token for the Discord application
# https://discordapp.com/developers/
BOT_TOKEN=

# The client ID and secret for the Reddit application
# https://www.reddit.com/prefs/apps/
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=

# The authentication settings for the database
MYSQL_HOST=
MYSQL_DB=
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_ROOT_PASSWORD=

# The path on your host file system to config.yml
CONFIG=

# The folder on your host file system for storing database data
DATABASE_FOLDER=

# The folder on your host file system for storing logs
LOGS_FOLDER=
```

**Step 3:** Create a `config.yml` file in the same folder using `config.default.yml` as the base and fill it out.

**Step 4:** Pull the Docker image and start the containers by running `docker-compose up -d` in the same folder.

## Contributing

Contributors are more than welcome to help make Chiya a better bot. If you are a developer, we encourage you to fork the bot, make changes, and PR your changes upstream. We ask that you read and adhere to our style guide for all PRs for consistency across the entire code base. PRs with no prior communication are not encouraged as your PR may not align with our ideals for the bot. Feel free to reach out for any questions or feedback.

### Style Guide
- [PEP8 as our style guide base.](https://peps.python.org/pep-0008/)
- [Black](https://github.com/psf/black) with `--line-length 120` instead of native 88.
- Comments and docstrings should aim to be 79 characters per line.
- Type hinting should be used for function declarations but not variable declarations.
- Keyword arguments are preferred for function calls even when the keyword is the same variable name as the function parameter.
- Imports should be in the following order: standard library imports, 3rd party dependency imports, and current project imports with a newline between each category of imports. `import <module>` lines should come before `from <module> import <object>` lines.
- There should be 2 newlines before and after global variables: after the last import and before the first class or function declaration.
- When breaking out of a function with a return, avoid returning nothing.
- Each function should have a brief docstring explaining what the function is doing. 
  - The starting `"""` and ending `"""` should be on lines by themselves even for one-line docstrings.
  - Docstrings should be written as sentences with proper capitalization, grammar, and punctuation.
  - Specifying parameters or return type in a docstring isn't necessary because we use type hinting.
- Comments should be minimal and explain why the code is doing something instead of what it is doing.
- Any messages logged to console should not contain ending punctuation.
- Any settings, keys, values, or IDs that may change on a deployment basis should be kept in the config file.
- All Discord commands and command parameters should have descriptions.
- All Discord commands should start with `await ctx.defer()` to avoid 3 second timeouts.
- There is no enforced git commit message style but keep your commit messages descriptive and self-explanatory.
