# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.8-slim-buster

ENV BOT_PREFIX=""
ENV BOT_TOKEN=""
ENV LOG_LEVEL="INFO"
ENV REDDIT_SUBREDDIT=""
ENV REDDIT_CLIENT_ID=""
ENV REDDIT_SECRET=""
ENV REDDIT_USER_AGENT=""

# (NOTE) I am not so sure about the following two envs are they actually needed?
# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app
COPY . /app

# (NOTE) I have never heard of requiring special user permission etc. inside a container where no volumes are mounted
# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
RUN useradd appuser && chown -R appuser /app
USER appuser


# (NOTE) Okay... I don't work with VS, but if it helps
# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "chiya.py"]
