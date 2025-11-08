FROM ghcr.io/astral-sh/uv:debian-slim
LABEL maintainer="https://github.com/snaacky/chiya"

# Setup environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Copy files to /app
WORKDIR /app
COPY . /app

# Setup venv and install packages
RUN uv sync
ENTRYPOINT ["uv", "run", "-m", "chiya.bot"]