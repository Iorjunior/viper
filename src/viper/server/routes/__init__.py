"""FastAPI route routers package."""

from viper.server.routes.assets import router as assets_router
from viper.server.routes.pipelines import router as pipelines_router
from viper.server.routes.runs import router as runs_router
from viper.server.routes.stages import router as stages_router

__all__ = [
    'assets_router',
    'pipelines_router',
    'runs_router',
    'stages_router',
]
