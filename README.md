<p align="center">
  <img src="assets/viper_logo.png" width="130" alt="Viper Logo" />
</p>

<h1 align="center">Viper</h1>

<p align="center">
  <strong>Local-first AI media processing platform.</strong><br>
  Transcribe, isolate, translate, synthesize, and dub media with zero cloud dependencies or seamless API fallbacks.
</p>

[![CI](https://github.com/Iorjunior/viper/actions/workflows/ci.yml/badge.svg)](https://github.com/Iorjunior/viper/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue.svg)](https://github.com/Iorjunior/viper/pkgs/container/viper)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/vue-3.5-brightgreen.svg)](https://vuejs.org/)

---

## ⚡ Quick Start (Docker One-Liner)

Run Viper in a single command. Includes the embedded web UI, SQLite database, background worker, and default local AI backends:

```bash
docker run -d \
  -p 8000:8000 \
  -v viper_data:/data \
  --name viper \
  ghcr.io/iorjunior/viper:latest
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## ✨ Features

- **🔒 100% Local-First & Private:** Process audio and video on your own hardware without sending media to external services.
- **🧩 Pluggable AI Backends:** Automatic hardware detection and runtime resolver for Apple Silicon (Metal/MLX), Linux/NVIDIA (CUDA), CPU, and optional OpenAI API fallbacks.
- **🎬 Pre-Built Media Pipelines:** Ready-to-run workflows for downloading, vocal isolation (Demucs), speech-to-text (Whisper), translation (LLM), speech synthesis (Kokoro), and video dubbing.
- **🖥️ Embedded Web Application:** Fast Vue 3 + Nuxt UI single-page application embedded directly in the server binary — browse pipelines in the Gallery, inspect real-time progress in Run Detail, or view and manage history.
- **🤖 Native Model Context Protocol (MCP) Server:** Built-in SSE transport at `/mcp/sse`. Connect AI agents (Cursor, Claude Desktop, Antigravity) to execute pipelines and query pipeline runs automatically.
- **⚙️ Async DAG Engine:** Topological task resolution with variable interpolation (`${stage_id.output_key}`) and async SQLite task queue.

---

## 🏗️ Architecture & Backends

Viper decouples the workflow orchestrator from concrete AI implementations using a unified backend registry.

| Capability | Backend Option | Target Environment | Acceleration |
|---|---|---|---|
| **Speech-to-Text (STT)** | `mlx_whisper` | macOS (Apple Silicon) | Metal (Unified Memory) |
| | `faster_whisper` *(default)* | Linux, macOS, Windows | CPU / NVIDIA CUDA |
| | `openai` | Any | Cloud API |
| **Text-to-Speech (TTS)** | `kokoro` *(default)* | Linux, macOS, Windows | CPU / Metal / CUDA (82M param) |
| | `openai` | Any | Cloud API |
| **Large Language Models (LLM)** | `mlx_lm` | macOS (Apple Silicon) | Metal (Native MLX weights) |
| | `openai` *(default)* | Any | OpenAI-compatible endpoint (Ollama, vLLM, LM Studio, Groq, OpenAI) |

---

## 🚀 Running with Docker Compose

To run Viper using Docker Compose with an OpenAI-compatible LLM endpoint (such as local Ollama, vLLM, LM Studio, or OpenAI):

```yaml
# docker-compose.yml
services:
  viper:
    image: ghcr.io/iorjunior/viper:latest
    container_name: viper
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///data/viper.db
      - VIPER_MEDIA_DIR=/data/media
      - VIPER_STT_BACKEND=faster_whisper
      - VIPER_TTS_BACKEND=kokoro
      - VIPER_LLM_BACKEND=openai
      - OPENAI_BASE_URL=http://host.docker.internal:11434/v1
      - OPENAI_MODEL=qwen2.5:1.5b
    volumes:
      - viper_data:/data
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped

volumes:
  viper_data:
```

Start the service:

```bash
docker compose up -d
```

---

## 📦 Built-In Pipelines

Viper ships with pre-configured declarative JSON manifests in `src/viper/pipelines/`:

1. **`download_video`**: Download videos from YouTube or direct URLs using `yt-dlp`.
2. **`transcribe_audio`**: Extract audio and generate timestamped text transcriptions via Whisper.
3. **`separate_audio`**: Separate vocal and accompaniment tracks using Demucs.
4. **`synthesize_speech`**: Generate speech audio from text using Kokoro or OpenAI TTS.
5. **`generate_subtitles`**: Transcribe speech and export standard SRT subtitle files.
6. **`dub_video`**: Full end-to-end pipeline: extracts audio, isolates vocals, transcribes speech, translates text via LLM, synthesizes target language audio, and remuxes into a dubbed video.

---

## 🤖 MCP (Model Context Protocol) Integration

Viper exposes an MCP server over SSE at `http://localhost:8000/mcp/sse`.

### Claude Desktop / Cursor Setup

Add Viper to your MCP configuration (`claude_desktop_config.json` or Cursor settings):

```json
{
  "mcpServers": {
    "viper": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

### Available MCP Tools

- `list_pipelines`: List all available media processing pipelines.
- `get_pipeline`: Retrieve manifest details and input parameters for a specific pipeline.
- `run_pipeline`: Trigger asynchronous execution of a pipeline with JSON inputs.
- `get_run_status`: Inspect status, stage progress, and outputs for a given run ID.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
