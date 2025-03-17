"""Main entry point for the Vantron Remote Media Server."""

import asyncio
import sys

from loguru import logger

from .server import MediaPlayerServer, get_server_config

# Configure loguru
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)
logger.add(
    "vantron-media-server.log",
    rotation="1 day",
    retention="7 days",
    compression="zip",
    level="DEBUG",
)


async def main() -> None:
    """Start the media player server."""
    try:
        host, port = get_server_config()
        server = MediaPlayerServer(host=host, port=port)
        await server.start()
    except Exception:
        logger.exception("Fatal error in media server")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception:
        logger.exception("Unexpected error")
        sys.exit(1)
