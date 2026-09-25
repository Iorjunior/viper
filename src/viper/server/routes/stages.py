"""Stage discovery and reflection API endpoints."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

import viper.stages  # noqa: F401 - ensure stages are registered
from viper.engine.registry import global_registry

router = APIRouter(prefix='/api/stages', tags=['stages'])


class StageResponse(BaseModel):
    """Public metadata for a registered pipeline stage."""

    name: str
    description: str = ''
    inputs: dict[str, Any]


@router.get('', response_model=list[StageResponse])
async def list_stages() -> list[StageResponse]:
    """List all registered processing stages and their input signatures."""
    definitions = global_registry.list_stages()
    return [
        StageResponse(
            name=d.name,
            description=d.description,
            inputs=d.inputs,
        )
        for d in definitions
    ]
