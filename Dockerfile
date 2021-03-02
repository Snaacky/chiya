# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.8-slim-buster
LABEL maintainer="https://github.com/ranimepiracy/Chiya"

ENV BOT_PREFIX="" \
  BOT_TOKEN="" \
  LOG_LEVEL="INFO" \
  REDDIT_SUBREDDIT="" \
  REDDIT_CLIENT_ID="" \
  REDDIT_SECRET="" \
  REDDIT_USER_AGENT="" \
  # Keeps Python from generating .pyc files in the container
  PYTHONDONTWRITEBYTECODE=1 \
  # Turns off buffering for easier container logging
  PYTHONUNBUFFERED=1

# Install pip requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Place where the app lives in the container
WORKDIR /app
COPY . /app

# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
RUN useradd discordbot && chown -R discordbot /app
USER discordbot

# For persistant data and ability to access data outside container
VOLUME [ "/app/DATABASE.db" ]
VOLUME [ "/app/config.yml" ]

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "chiya.py"]
