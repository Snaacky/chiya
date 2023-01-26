# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11.1-slim-bullseye
LABEL maintainer="https://github.com/snaacky/chiya"

# Keeps Python from generating .pyc files in the container
# Turns off buffering for easier container logging
# Force UTF8 encoding for funky character handling
# Needed so imports function properly
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 
ENV PYTHONIOENCODING=utf-8
ENV PYTHONPATH=/app

# Install MySQL and Poetry
RUN apt update -y
RUN apt install --no-install-recommends -y build-essential libmariadb-dev-compat libmariadb-dev python3-mysqldb git curl
RUN curl -sSL https://install.python-poetry.org | python -

# Add Poetry path to PATH
ENV PATH="${PATH}:/root/.local/bin"

# Install project dependencies with Poetry
COPY pyproject.toml .
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi --only main --all-extras

# Place where the app lives in the container
WORKDIR /app
COPY . /app

# During debugging, this entry point will be overridden. 
CMD ["python", "/app/chiya/bot.py"]
