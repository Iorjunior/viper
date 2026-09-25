.PHONY: install install-apple install-remote dev server worker migrate \
        ui-install ui-dev ui-build \
        test lint fmt type-check \
        docker-build docker-run

# ── Python / Backend ──────────────────────────────────────────────────────────
install:
	uv sync --extra dev

install-apple:
	uv sync --extra apple --extra dev

install-remote:
	uv sync --extra remote --extra dev

migrate:
	uv run alembic upgrade head

server:
	uv run uvicorn viper.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	uv run viper-worker

# ── UI ────────────────────────────────────────────────────────────────────────
ui-install:
	pnpm --filter ui install

ui-dev:
	pnpm --filter ui dev

ui-build:
	pnpm --filter ui build

# ── Dev (all together) ────────────────────────────────────────────────────────
dev: migrate
	uv run uvicorn viper.main:app --reload --port 8000 & \
	uv run viper-worker & \
	pnpm --filter ui dev

# ── Quality ───────────────────────────────────────────────────────────────────
test:
	uv run pytest --tb=short

lint:
	uv run ruff check src/
	pnpm --filter ui lint

fmt:
	uv run ruff format src/
	pnpm --filter ui exec prettier --write src/

fmt-check:
	uv run ruff format --check src/
	pnpm --filter ui exec prettier --check src/

type-check:
	uv run pyright src/
	pnpm --filter ui exec vue-tsc --noEmit

# ── Docker ────────────────────────────────────────────────────────────────────
docker-build:
	pnpm --filter ui build
	docker build -t viper .

docker-run:
	docker run -p 8000:8000 -v viper_data:/data viper

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  install        Install Python deps (+ dev extras)"
	@echo "  install-apple  Install with Apple Silicon (MLX) extras"
	@echo "  migrate        Run Alembic migrations"
	@echo "  dev            Start backend + worker + UI dev server"
	@echo "  server         Start FastAPI server only"
	@echo "  worker         Start pipeline worker only"
	@echo "  ui-dev         Start Vite dev server"
	@echo "  ui-build       Build UI for production"
	@echo "  test           Run pytest"
	@echo "  lint           Lint Python + UI"
	@echo "  fmt            Format Python + UI"
	@echo "  type-check     Pyright + vue-tsc"
	@echo "  docker-build   Build Docker image"
	@echo "  docker-run     Run Docker container"
	@echo ""
