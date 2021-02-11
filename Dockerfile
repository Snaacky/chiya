# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.8-slim-buster

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

WORKDIR /app
COPY . /app

# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
RUN useradd appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "chiya.py"]
