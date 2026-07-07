import asyncio
import json
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """Tracks active WebSocket connections grouped by space public_id."""

    def __init__(self):
        self._conns: dict[str, set[WebSocket]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, space_pid: str, ws: WebSocket):
        await ws.accept()
        self._conns[space_pid].add(ws)
        self._loop = asyncio.get_running_loop()

    def disconnect(self, space_pid: str, ws: WebSocket):
        self._conns[space_pid].discard(ws)
        if not self._conns[space_pid]:
            self._conns.pop(space_pid, None)

    async def broadcast(self, space_pid: str, message: dict):
        dead = []
        for ws in list(self._conns.get(space_pid, set())):
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(space_pid, ws)

    def broadcast_threadsafe(self, space_pid: str, message: dict):
        """Callable from sync (non-async) route handlers."""
        if not self._loop or not self._conns.get(space_pid):
            return
        try:
            asyncio.run_coroutine_threadsafe(self.broadcast(space_pid, message), self._loop)
        except Exception:
            pass


manager = ConnectionManager()


@router.websocket("/api/ws/{space_id}")
async def ws_endpoint(websocket: WebSocket, space_id: str):
    await manager.connect(space_id, websocket)
    try:
        while True:
            # We don't require client messages; just keep the connection open.
            # Receiving also lets us detect disconnects promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(space_id, websocket)
    except Exception:
        manager.disconnect(space_id, websocket)
