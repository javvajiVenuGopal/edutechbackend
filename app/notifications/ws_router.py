from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from jose import jwt
from app.auth.utils import SECRET_KEY, ALGORITHM
from app.notifications.ws_manager import manager

notification_ws_router  = APIRouter( prefix="/notifications",
    tags=["Notification"])


@notification_ws_router .websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):

    token = websocket.query_params.get("token")

    if not token:
        await websocket.close()
        return

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("user_id")

        if not user_id:
            await websocket.close()
            return

        await manager.connect(user_id, websocket)

        print("✅ Notification socket connected:", user_id)

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:

        manager.disconnect(user_id)

        print("❌ Notification socket disconnected:", user_id)