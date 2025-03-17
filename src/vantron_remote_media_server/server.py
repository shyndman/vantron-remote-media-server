"""WebSocket server implementation for the van's media player."""

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import websockets
from loguru import logger
from websockets.exceptions import ConnectionClosed
from websockets.server import ServerConnection

# Environment variable configuration
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9300


def get_server_config() -> tuple[str, int]:
    """Get server configuration from environment variables."""
    host = os.environ.get("VANTRON_MEDIA_HOST", DEFAULT_HOST)
    try:
        port = int(os.environ.get("VANTRON_MEDIA_PORT", DEFAULT_PORT))
    except ValueError:
        logger.warning(f"Invalid port specified, using default: {DEFAULT_PORT}")
        port = DEFAULT_PORT
    return host, port


@dataclass
class PlayerState:
    """Represents the current state of the van's media player."""

    state: str = "idle"  # idle, playing, paused, error
    media: Optional[Dict[str, Any]] = None
    volume: float = 1.0
    muted: bool = False
    error: Optional[str] = None


class MediaPlayerServer:
    """WebSocket server that handles JSON-RPC requests for van's media playback."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.state = PlayerState()
        self.connections: set[ServerConnection] = set()

    async def start(self) -> None:
        """Start the WebSocket server."""
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info(f"Van media server started on ws://{self.host}:{self.port}")
            await asyncio.Future()  # run forever

    async def handle_client(self, websocket: ServerConnection) -> None:
        """Handle a client connection."""
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"New client connected from {client_info}")

        self.connections.add(websocket)
        try:
            # Send initial state
            await self.send_state_update(websocket)

            # Handle incoming messages
            async for message in websocket:
                try:
                    request = json.loads(message)
                    logger.debug(f"Received request from {client_info}: {request}")
                    response = await self.handle_request(request)
                    if response:
                        await websocket.send(json.dumps(response))
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received from {client_info}")
                    await self.send_error(websocket, -32700, "Parse error")
                except Exception:
                    logger.exception(f"Error handling message from {client_info}")
                    await self.send_error(websocket, -32603, "Internal error")
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_info}")
        finally:
            self.connections.remove(websocket)

    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a JSON-RPC request."""
        if "method" not in request:
            return self.create_error_response(
                request.get("id"), -32600, "Invalid request"
            )

        method = request["method"]
        params = request.get("params", {})
        request_id = request.get("id")

        # Only process requests with IDs (notifications don't get responses)
        if request_id is None:
            return None

        handler = getattr(self, f"handle_{method}", None)
        if not handler:
            logger.warning(f"Method not found: {method}")
            return self.create_error_response(request_id, -32601, "Method not found")

        try:
            result = await handler(params)
            return {"jsonrpc": "2.0", "result": result, "id": request_id}
        except Exception as e:
            logger.exception(f"Error handling {method}")
            return self.create_error_response(request_id, -32603, str(e))

    async def broadcast_state(self) -> None:
        """Broadcast state update to all connected clients."""
        if not self.connections:
            return

        message = {
            "jsonrpc": "2.0",
            "method": "stateChanged",
            "params": self.get_state_dict(),
        }
        websockets.broadcast(self.connections, json.dumps(message))
        logger.debug(f"State broadcast to {len(self.connections)} clients")

    async def send_state_update(self, websocket: ServerConnection) -> None:
        """Send current state to a specific client."""
        message = {
            "jsonrpc": "2.0",
            "method": "stateChanged",
            "params": self.get_state_dict(),
        }
        await websocket.send(json.dumps(message))
        logger.debug(
            f"State sent to {websocket.remote_address[0]}:{websocket.remote_address[1]}"
        )

    async def send_error(
        self, websocket: ServerConnection, code: int, message: str
    ) -> None:
        """Send an error message to a client."""
        error_msg = {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": None,
        }
        await websocket.send(json.dumps(error_msg))
        logger.debug(
            f"Error sent to {websocket.remote_address[0]}:{websocket.remote_address[1]}: {message}"
        )

    def create_error_response(
        self, request_id: Any, code: int, message: str
    ) -> Dict[str, Any]:
        """Create a JSON-RPC error response."""
        return {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": request_id,
        }

    def get_state_dict(self) -> Dict[str, Any]:
        """Get the current state as a dictionary."""
        return {
            "state": self.state.state,
            "media": self.state.media,
            "volume": self.state.volume,
            "muted": self.state.muted,
            "error": self.state.error,
        }

    # JSON-RPC method handlers

    async def handle_getState(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle getState method."""
        return self.get_state_dict()

    async def handle_getSupportedMediaTypes(self, params: Dict[str, Any]) -> list[str]:
        """Handle getSupportedMediaTypes method."""
        return ["music"]  # Only supporting audio playback

    # Placeholder handlers for media control methods
    # These will be implemented later with actual audio playback logic

    async def handle_play(self, params: Dict[str, Any]) -> bool:
        """Handle play method."""
        if self.state.state == "paused":
            self.state.state = "playing"
            logger.info("Playback resumed")
            await self.broadcast_state()
        return True

    async def handle_pause(self, params: Dict[str, Any]) -> bool:
        """Handle pause method."""
        if self.state.state == "playing":
            self.state.state = "paused"
            logger.info("Playback paused")
            await self.broadcast_state()
        return True

    async def handle_stop(self, params: Dict[str, Any]) -> bool:
        """Handle stop method."""
        self.state.state = "idle"
        self.state.media = None
        logger.info("Playback stopped")
        await self.broadcast_state()
        return True

    async def handle_setVolume(self, params: Dict[str, Any]) -> bool:
        """Handle setVolume method."""
        if "level" in params:
            level = max(0.0, min(1.0, float(params["level"])))
            self.state.volume = level
            logger.info(f"Volume set to {level:.2%}")
            await self.broadcast_state()
        return True

    async def handle_load(self, params: Dict[str, Any]) -> bool:
        """Handle load method."""
        if "url" not in params:
            raise ValueError("URL is required")

        url = params["url"]
        logger.info(f"Loading media from {url}")

        self.state.media = {
            "url": url,
            "media_type": "music",
            "duration": 0.0,
            "position": 0.0,
        }
        self.state.state = (
            "playing" if params.get("options", {}).get("autoplay", True) else "paused"
        )
        await self.broadcast_state()
        return True
