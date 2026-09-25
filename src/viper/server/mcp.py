"""Model Context Protocol (MCP) server for external AI agent integration."""

import json
from typing import Any

from mcp.server.mcpserver import MCPServer

import viper.stages  # noqa: F401 - ensure stages are registered
from viper.db.models import Run
from viper.db.repositories import RunRepository, StageRunRepository
from viper.db.session import async_session_maker
from viper.engine.manifest_loader import (
    get_manifest,
    load_manifests_from_dir,
    register_manifest,
)
from viper.engine.models import PipelineManifest
from viper.engine.registry import global_registry
from viper.worker.queue import enqueue

mcp_server = MCPServer('Viper')


@mcp_server.tool(
    name='list_pipelines',
    description=(
        'List all available pipelines with metadata and input schemas.'
    ),
)
async def list_pipelines() -> list[dict[str, Any]]:
    """List all available pipeline manifests."""
    manifests = load_manifests_from_dir()
    return [
        {
            'id': manifest.id,
            'name': manifest.name,
            'description': manifest.description,
            'inputs': manifest.inputs,
            'tags': manifest.tags,
        }
        for manifest in manifests.values()
    ]


@mcp_server.tool(
    name='run_pipeline',
    description='Trigger execution of a registered pipeline by ID.',
)
async def run_pipeline(
    pipeline_id: str,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Create a pending run record for a named pipeline."""
    manifest = get_manifest(pipeline_id)
    if not manifest:
        return {'error': f"Pipeline '{pipeline_id}' not found"}

    run = Run(
        pipeline_id=pipeline_id,
        status='pending',
        inputs=json.dumps(inputs),
    )
    async with async_session_maker() as session:
        repo = RunRepository(session)
        created = await repo.create(run)
        enqueue(created.id)
        return {
            'id': created.id,
            'pipeline_id': created.pipeline_id,
            'status': created.status,
            'inputs': created.inputs,
            'created_at': created.created_at.isoformat(),
        }


@mcp_server.tool(
    name='run_custom_pipeline',
    description='Trigger execution of an ad-hoc custom pipeline manifest.',
)
async def run_custom_pipeline(
    manifest: dict[str, Any],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Create a pending run record for an inline pipeline manifest."""
    try:
        parsed_manifest = PipelineManifest.model_validate(manifest)
    except Exception as exc:
        return {'error': f'Invalid pipeline manifest: {exc}'}

    register_manifest(parsed_manifest)

    run = Run(
        pipeline_id=parsed_manifest.id,
        status='pending',
        inputs=json.dumps(inputs),
    )
    async with async_session_maker() as session:
        repo = RunRepository(session)
        created = await repo.create(run)
        enqueue(created.id)
        return {
            'id': created.id,
            'pipeline_id': created.pipeline_id,
            'status': created.status,
            'inputs': created.inputs,
            'created_at': created.created_at.isoformat(),
        }


@mcp_server.tool(
    name='get_run_status',
    description='Fetch status, outputs, and stage progress for any run.',
)
async def get_run_status(run_id: str) -> dict[str, Any]:
    """Query run details and associated stage runs by ID."""
    async with async_session_maker() as session:
        run_repo = RunRepository(session)
        stage_repo = StageRunRepository(session)

        run = await run_repo.get(run_id)
        if not run:
            return {'error': f"Run '{run_id}' not found"}

        stages = await stage_repo.list_by_run(run_id)
        return {
            'id': run.id,
            'pipeline_id': run.pipeline_id,
            'status': run.status,
            'inputs': run.inputs,
            'outputs': run.outputs,
            'created_at': run.created_at.isoformat(),
            'finished_at': (
                run.finished_at.isoformat() if run.finished_at else None
            ),
            'stage_runs': [
                {
                    'id': s.id,
                    'stage_id': s.stage_id,
                    'status': s.status,
                    'output': s.output,
                    'error': s.error,
                }
                for s in stages
            ],
        }


@mcp_server.tool(
    name='list_stages',
    description='List all registered processing stages and input parameters.',
)
async def list_stages() -> list[dict[str, Any]]:
    """List registered stage definitions from the engine registry."""
    definitions = global_registry.list_stages()
    return [
        {
            'name': d.name,
            'description': d.description,
            'inputs': d.inputs,
        }
        for d in definitions
    ]
