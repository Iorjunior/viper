# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-30

### Added

- **Core Workflow Engine**:
  - Declarative DAG pipeline execution with topological sorting and cycle detection.
  - `@stage` decorator and registry for modular Python execution units.
  - Variable interpolation supporting inputs (`${inputs.key}`) and upstream stage outputs (`${stage_id.output_key}`).
  - Centralized media asset management for intermediate and final outputs.

- **Pluggable AI Backends**:
  - **Speech-to-Text (STT)**: `mlx_whisper` (Apple Silicon Metal acceleration), `faster_whisper` (CPU / CUDA), and `openai` (Cloud API).
  - **Text-to-Speech (TTS)**: `kokoro` (ultra-fast, lightweight 82M parameter local model) and `openai` (Cloud API).
  - **Large Language Models (LLM)**: `mlx_lm` (native Apple Silicon weights) and `openai` (universal OpenAI-compatible backend for Ollama, vLLM, LM Studio, Groq, and OpenAI).
  - Hardware-aware dynamic backend resolver.

- **Built-in Pipeline Manifests**:
  - `download_video`: Extract video streams from YouTube or direct URLs via `yt-dlp`.
  - `transcribe_audio`: Audio transcription with timestamped speech segments.
  - `separate_audio`: Vocal and accompaniment separation using Demucs.
  - `synthesize_speech`: Text-to-speech audio synthesis.
  - `generate_subtitles`: Speech transcription and standard SRT subtitle generation.
  - `dub_video`: Complete automated dubbing pipeline (download/extract, isolate vocals, transcribe, LLM translate, TTS speech synthesis, audio mixing, and video remuxing).

- **API & Background Worker**:
  - FastAPI async web service providing REST endpoints for pipelines, stages, runs, and asset streaming.
  - Real-time WebSocket broadcasting (`/ws/{run_id}`) for live stage execution updates.
  - Native Model Context Protocol (MCP) server over SSE at `/mcp/sse` for AI agent integrations (Cursor, Claude Desktop, Antigravity).
  - Asynchronous SQLite task queue worker with graceful shutdown handling.

- **Embedded Web Dashboard**:
  - Single-page application built with Vue 3, Vite, Nuxt UI, and Tailwind CSS.
  - **Pipeline Gallery**: Search, filter, and inspect built-in pipeline manifests.
  - **Pipeline Form**: Dynamic input generation tailored to pipeline schemas.
  - **Run Detail & History**: Real-time progress timeline, status indicators, and embedded audio/video player.
  - **Visual Builder**: Interactive drag-and-drop DAG workflow editor using Vue Flow.

- **Deployment & Automation**:
  - Multi-stage `Dockerfile` with embedded frontend assets and zero Node.js runtime footprint.
  - `docker-compose.yml` for standalone zero-configuration deployment.
  - GitHub Actions CI matrix running linters (`ruff`, `eslint`, `prettier`), typecheckers (`pyright`, `vue-tsc`), and test suites (`pytest`, `vitest`).
  - Automated release workflow publishing Docker containers to GitHub Container Registry (GHCR) on version tags.
