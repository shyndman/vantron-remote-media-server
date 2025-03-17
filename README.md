# Vantron Remote Media Server

A WebSocket-based media server that implements the JSON-RPC 2.0 protocol for playing audio over the van's speaker system. This server is designed to be controlled by Home Assistant through the `hass-remote-media-player` integration.

## Features

- JSON-RPC 2.0 WebSocket API
- Audio playback control (play, pause, stop)
- Volume control
- Media state reporting
- Seamless integration with Home Assistant
- Optimized for van's audio system

## Requirements

- Python 3.10 or higher
- `uv` package manager (recommended)
- Access to van's audio system

## Installation

1. Clone the repository
2. Install dependencies using `uv`:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e .
   ```

## Development

Install development dependencies:
```bash
uv pip install -e ".[dev]"
```

## Usage

Start the server:
```bash
python -m vantron_remote_media_server
```

The server will listen on port 9300 by default.

## Configuration

The server can be configured using environment variables:
- `VANTRON_MEDIA_HOST`: Host to bind to (default: "0.0.0.0")
- `VANTRON_MEDIA_PORT`: Port to listen on (default: 9300)

## License

MIT
