# Stage 1: Build frontend UI
FROM node:22-slim AS ui-builder

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN npm install -g pnpm@10.33.0

WORKDIR /app

# Copy package configurations for pnpm workspace
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY ui/package.json ./ui/

RUN pnpm --filter ui install --frozen-lockfile

# Copy UI source code and build production assets
COPY ui ./ui
RUN pnpm --filter ui build

# Stage 2: Production Python runtime
FROM python:3.12-slim AS runner

# Install system dependencies (ffmpeg, libsndfile1 for audio/video processing, build-essential and libopus-dev for native extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libopus-dev \
    curl \
    build-essential \
    pkg-config \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV CMAKE_POLICY_VERSION_MINIMUM=3.5

# Install uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files and install production virtualenv dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source, migrations, and entrypoint
COPY README.md alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY docker/entrypoint.sh ./docker/entrypoint.sh
RUN chmod +x ./docker/entrypoint.sh
RUN uv sync --frozen --no-dev

# Copy compiled frontend assets from Stage 1
COPY --from=ui-builder /app/ui/dist ./ui/dist

# Default environment configurations
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    VIPER_UI_DIST=/app/ui/dist \
    DATABASE_URL=sqlite+aiosqlite:////data/viper.db \
    VIPER_MEDIA_DIR=/data/media \
    PATH="/app/.venv/bin:$PATH"

# Persistent storage volume for database and media assets
VOLUME ["/data"]

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
