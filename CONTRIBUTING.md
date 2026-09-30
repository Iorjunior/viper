# Contributing to Viper

Thank you for your interest in contributing to Viper!  
Viper is a local-first AI media processing platform designed to be simple, fast, and modular.

---

## 🛠️ Local Development Setup

### Prerequisites

- **Python 3.12+** with [`uv`](https://github.com/astral-sh/uv)
- **Node.js 22+** with [`pnpm`](https://pnpm.io/)
- **System packages**: `ffmpeg` and `libsndfile`
  - macOS: `brew install ffmpeg libsndfile`
  - Ubuntu/Debian: `sudo apt install -y ffmpeg libsndfile1`

### Initial Installation

```bash
# Clone the repository
git clone https://github.com/Iorjunior/viper.git
cd viper

# Setup Python virtualenv and install dependencies
uv sync --extra dev

# (Optional) On Apple Silicon for local MLX hardware acceleration:
uv sync --extra dev --extra apple

# Install frontend UI dependencies
pnpm --filter ui install
```

### Database Migrations

Apply database migrations using Alembic:

```bash
uv run alembic upgrade head
```

### Running the Services Locally

Run the API server, background worker, and Vite dev server in parallel:

```bash
# Terminal 1: FastAPI API Server
uv run uvicorn viper.main:app --reload --port 8000

# Terminal 2: Background Task Worker
uv run viper-worker

# Terminal 3: Vite Dev Server for UI
pnpm --filter ui dev
```

Visit the development UI at [http://localhost:5173](http://localhost:5173).

---

## 📐 Code Style & Quality Standards

We enforce strict quality and formatting checks across both backend and frontend.

### Backend (Python)

- **Ruff**: Linting and formatting.
  ```bash
  uv run ruff check src/ tests/
  uv run ruff format --check src/ tests/
  ```
- **Pyright**: Static type checking.
  ```bash
  uv run pyright src/
  ```
- **Pytest**: Unit and integration test suite with coverage report.
  ```bash
  uv run pytest
  ```

### Frontend (Vue 3 / TypeScript)

- **ESLint & Prettier**: Code formatting and linting.
  ```bash
  pnpm --filter ui lint
  pnpm --filter ui fmt:check
  ```
- **vue-tsc**: TypeScript compilation check.
  ```bash
  pnpm --filter ui type-check
  ```
- **Vitest**: Unit testing for components and composables.
  ```bash
  pnpm --filter ui test:run
  pnpm --filter ui build
  ```

### Commit Guidelines

We follow **Conventional Commits**:

- `feat:` New features or stages
- `fix:` Bug fixes
- `docs:` Documentation improvements
- `refactor:` Code refactoring without behavior change
- `test:` Adding or updating tests
- `chore:` Dependency or tooling updates

---

## 🧩 Extensibility Guides

### 1. How to Add a New `@stage`

All execution units in Viper are decorated Python functions registered with `@stage`.

1. Create or edit a module in `src/viper/stages/` (e.g., `src/viper/stages/audio.py`):
   ```python
   from typing import Any
   from viper.engine.decorator import stage

   @stage(
       name="normalize_audio",
       description="Normalize audio loudness and convert to WAV",
   )
   def normalize_audio(audio_path: str, target_db: float = -14.0) -> dict[str, Any]:
       # Process media here...
       normalized_path = "/path/to/output.wav"
       return {"normalized_audio": normalized_path}
   ```
2. Ensure the stage is imported in `src/viper/stages/__init__.py`.
3. Add a unit test in `tests/test_stages.py`.

### 2. How to Add a New Pipeline Manifest

Pipelines are declared as JSON files in `src/viper/pipelines/`:

1. Create a JSON file (e.g., `src/viper/pipelines/normalize_pipeline.json`):
   ```json
   {
     "id": "normalize_pipeline",
     "name": "Audio Normalization",
     "description": "Normalize uploaded audio loudness level",
     "tags": ["audio", "loudness"],
     "builtin": true,
     "inputs": {
       "audio_path": {
         "type": "file",
         "description": "Source audio file"
       }
     },
     "stages": [
       {
         "id": "normalize",
         "stage": "normalize_audio",
         "inputs": {
           "audio_path": "${inputs.audio_path}",
           "target_db": -16.0
         }
       }
     ]
   }
   ```
2. The pipeline will automatically load on server startup and appear in the Gallery.
3. Add a test in `tests/test_manifests.py`.

### 3. How to Add a New Backend

Viper defines abstract base contracts for AI capabilities in `src/viper/backends/`:

- `STTBackend` in `src/viper/backends/stt/base.py`
- `TTSBackend` in `src/viper/backends/tts/base.py`
- `LLMBackend` in `src/viper/backends/llm/base.py`

To add a new backend:
1. Subclass the corresponding base class in `src/viper/backends/<type>/<backend_name>.py`.
2. Implement required abstract methods (e.g., `transcribe()`, `synthesize_raw()`, or `translate()`).
3. Add resolution logic to `src/viper/backends/resolver.py` (e.g., in `get_stt()`, `get_tts()`, or `get_llm()`).
4. Add unit tests with mock fixtures in `tests/test_backends.py`.

---

## 🚀 Submitting a Pull Request

1. Fork the repository and create a feature branch (`git checkout -b feat/my-new-feature`).
2. Make your changes adhering to KISS / YAGNI principles.
3. Ensure all backend tests and frontend checks pass:
   ```bash
   uv run ruff check src/ tests/
   uv run pyright src/
   uv run pytest
   pnpm --filter ui lint
   pnpm --filter ui type-check
   pnpm --filter ui test:run
   ```
4. Commit using Conventional Commits.
5. Push to your fork and submit a Pull Request to `main`.
