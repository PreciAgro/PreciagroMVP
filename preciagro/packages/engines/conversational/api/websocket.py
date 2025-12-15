from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..session.session_store import SessionStore
from ..integrations.agrollm_client import AgroLLMClient
from .rest import session_store, agrollm_client  # Import singletons

router = APIRouter()


@router.websocket("/v1/sessions/{session_id}/stream")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            user_text = data.get("text")

            # Simplified flow for streaming:
            # 1. Get Session
            session = session_store.get_session(session_id)
            if not session:
                await websocket.send_json({"error": "Session not found"})
                continue

            # 2. Build Prompt (Simplified)
            prompt_payload = {
                "prompt": user_text,  # In real app, use PromptManager
                "model_mode": "pretrained",
            }

            # 3. Stream from AgroLLM
            for chunk in agrollm_client.stream_response(prompt_payload):
                await websocket.send_json(chunk)

    except WebSocketDisconnect:
        print(f"Client disconnected from session {session_id}")
