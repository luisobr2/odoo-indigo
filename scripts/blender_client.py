"""
Minimal Python client for the BlenderMCP addon (https://github.com/ahujasid/blender-mcp).

The addon listens on TCP localhost:9876 and accepts newline-terminated JSON
commands of the form:

    {"type": "command_name", "params": {...}}

The most useful command is `execute_code` which runs arbitrary Python inside
Blender — that's how we'll build doors, apply materials, and export GLBs.
"""
from __future__ import annotations

import json
import socket
import sys
from typing import Any


class BlenderClient:
    def __init__(self, host: str = '127.0.0.1', port: int = 9876, timeout: float = 30.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def _recv_json(self, sock: socket.socket) -> dict[str, Any]:
        chunks = bytearray()
        sock.settimeout(self.timeout)
        while True:
            chunk = sock.recv(8192)
            if not chunk:
                break
            chunks.extend(chunk)
            try:
                return json.loads(chunks.decode())
            except json.JSONDecodeError:
                continue
        raise RuntimeError(f'Incomplete response: {chunks.decode(errors="replace")[:300]}')

    def send(self, command: str, params: dict[str, Any] | None = None) -> Any:
        msg = json.dumps({'type': command, 'params': params or {}}).encode()
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.sendall(msg)
            resp = self._recv_json(sock)
        if resp.get('status') != 'success':
            raise RuntimeError(f'Blender error: {resp.get("message")}\n'
                               f'Full response: {json.dumps(resp)[:1000]}')
        return resp.get('result', resp)

    def execute(self, python_code: str) -> Any:
        """Run arbitrary Python inside Blender. The script must set a `result`
        variable that the addon JSON-serializes back to us."""
        return self.send('execute_code', {'code': python_code})

    def ping(self) -> dict[str, Any]:
        return self.send('get_scene_info')


if __name__ == '__main__':
    c = BlenderClient()
    try:
        info = c.ping()
        print('Connected to BlenderMCP.')
        print(json.dumps(info, indent=2)[:1500])
    except Exception as e:
        print(f'Failed: {e}', file=sys.stderr)
        sys.exit(1)
