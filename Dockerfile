# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.10.0-slim-buster
LABEL maintainer="https://github.com/ranimepiracy/Chiya"

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1 \
  # Turns off buffering for easier container logging
  PYTHONUNBUFFERED=1 \
  # Force UTF8 encoding for funky characters
  PYTHONIOENCODING=utf8

# Install MySQL and poetry
RUN apt-get update -y && \
    apt-get install --no-install-recommends -y build-essential libmariadb-dev-compat libmariadb-dev python-mysqldb git curl \
    && curl -sSL https://install.python-poetry.org | python -

# add poetry path to PATH
ENV PATH="${PATH}:/root/.local/bin"

# Install project dependencies with poetry
COPY pyproject.toml .
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --extras "aiodns Brotlipy cchardet orjson"

# Place where the app lives in the container
WORKDIR /app
COPY . /app

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "/app/chiya/bot.py"]