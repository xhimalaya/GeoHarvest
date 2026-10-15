import json
import asyncio
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.core.jobs.engine import job_engine

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._loop = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self._loop = asyncio.get_event_loop()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, data: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(data))
            except Exception:
                self.disconnect(connection)

    def on_job_event(self, event_data: dict):
        if self._loop and self.active_connections:
            asyncio.run_coroutine_threadsafe(self.broadcast_json(event_data), self._loop)


ws_manager = ConnectionManager()
# Connect job engine event listener
job_engine.add_listener(ws_manager.on_job_event)


@router.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive ping/pong
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
