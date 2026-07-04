from fastapi import WebSocket


class ConnectionManager:

    def __init__(self):

        self.connections = []

    async def connect(self, websocket: WebSocket):

        await websocket.accept()

        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):

        if websocket in self.connections:

            self.connections.remove(websocket)

    async def broadcast(self, data):

        dead = []

        for ws in self.connections:

            try:

                await ws.send_json(data)

            except:

                dead.append(ws)

        for ws in dead:

            self.disconnect(ws)


manager = ConnectionManager()
