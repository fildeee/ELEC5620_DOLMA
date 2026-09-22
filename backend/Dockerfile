# uv provides both the interpreter and the dependency installer.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Prevent Python from writing .pyc files and buffering output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# docker-compose bind-mounts ./backend over /app for live reload, which would hide
# a virtualenv living at /app/.venv. Keeping it outside the mount point avoids that,
# and also stops the host's macOS venv from shadowing the container's Linux one.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# Copy packages in rather than hard-linking them from uv's cache, which sits on a
# different filesystem here.
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

# Install dependencies before copying the source, so this layer is reused until the
# lockfile itself changes. --frozen fails loudly if uv.lock is out of date with
# pyproject.toml instead of silently resolving something else.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy the rest of the backend files into the container
COPY . .

# Expose Flask port
EXPOSE 5000

# Run your app
CMD ["python", "app.py"]
