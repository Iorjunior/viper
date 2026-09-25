"""FastAPI core application configuration and route registration."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.transport_security import TransportSecuritySettings

from viper.db.session import init_db
from viper.engine.manifest_loader import ManifestLoader
from viper.server.mcp import mcp_server
from viper.server.routes import (
    assets_router,
    pipelines_router,
    runs_router,
    stages_router,
)
from viper.server.ws import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handling database initialization and manifest loading."""
    await init_db()
    ManifestLoader().load_all()
    yield


app = FastAPI(
    title='Viper',
    version='0.1.0',
    description='Local-first AI media processing platform',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/api/health')
async def health_check() -> dict[str, Any]:
    """Health check endpoint confirming API status."""
    return {'status': 'ok', 'version': app.version}


@app.websocket('/ws/{run_id}')
async def websocket_run_endpoint(websocket: WebSocket, run_id: str) -> None:
    """WebSocket endpoint broadcasting real-time progress for a run."""
    await ws_manager.connect(run_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, websocket)


app.include_router(pipelines_router)
app.include_router(stages_router)
app.include_router(runs_router)
app.include_router(assets_router)

# Mount Model Context Protocol (MCP) server SSE sub-application
app.mount(
    '/mcp/sse',
    mcp_server.sse_app(
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        )
    ),
)
