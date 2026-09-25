"""CLI entrypoint and application server runner."""

import uvicorn

from viper.config import HOST, LOG_LEVEL, PORT
from viper.server.app import app

__all__ = ['app', 'serve']


def serve() -> None:
    """Run FastAPI application server using Uvicorn."""
    uvicorn.run(
        'viper.server.app:app',
        host=HOST,
        port=PORT,
        log_level=LOG_LEVEL.lower(),
        reload=True,
    )


if __name__ == '__main__':
    serve()
