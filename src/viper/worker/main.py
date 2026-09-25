"""Command-line entrypoint for the background pipeline worker."""

import asyncio
import logging
import signal

from viper.db.session import init_db
from viper.engine.manifest_loader import ManifestLoader
from viper.worker.runner import WorkerRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('viper.worker')


async def run_worker() -> None:
    """Initialize database, load manifests, and start worker loop."""
    logger.info('Initializing Viper worker...')
    await init_db()
    ManifestLoader().load_all()

    runner = WorkerRunner()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, runner.stop)
        except NotImplementedError:
            # Handle systems without signal handlers (e.g. threads/Windows)
            pass

    logger.info('Worker started, listening for runs...')
    await runner.run_loop()
    logger.info('Worker stopped cleanly.')


def main() -> None:
    """CLI script entrypoint for viper-worker."""
    try:
        asyncio.run(run_worker())
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info('Worker shutdown requested.')


if __name__ == '__main__':
    main()
