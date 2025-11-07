FROM ghcr.io/astral-sh/uv:0.9.8-python3.14-bookworm-slim
LABEL maintainer="https://github.com/snaacky/chiya"

# Setup environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 
ENV PYTHONIOENCODING=utf-8
ENV PYTHONPATH=/app

# Copy files to /app
WORKDIR /app
COPY . /app

# Setup venv and install packages
RUN uv sync
ENTRYPOINT ["uv", "run", "python", "chiya/bot.py"]