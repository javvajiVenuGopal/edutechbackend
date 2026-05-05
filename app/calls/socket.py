import asyncio

class ConnectionManager:

    def __init__(self):
        self.active_connections = {}

    async def connect(self, user_id, websocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id):
        self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id, data):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(data)


manager = ConnectionManager()