from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from ..session.session_store import SessionStore
from ..session.memory_manager import MemoryManager
from ..prompts.prompt_manager import PromptManager
from ..dialog.dialog_policy import DialogPolicy
from ..dialog.safety_ui import SafetyUI
from ..integrations.agrollm_client import AgroLLMClient
from ..integrations.image_analysis_client import ImageAnalysisClient
from ..integrations.geo_client import GeoClient
from ..integrations.temporal_client import TemporalClient
from ..integrations.crop_client import CropClient
from ..integrations.feedback_client import FeedbackClient

router = APIRouter()

# Instantiate services (Singleton pattern for simplicity here)
session_store = SessionStore()
memory_manager = MemoryManager()
prompt_manager = PromptManager()
dialog_policy = DialogPolicy()
safety_ui = SafetyUI()
agrollm_client = AgroLLMClient()
image_client = ImageAnalysisClient()
geo_client = GeoClient()
temporal_client = TemporalClient()
crop_client = CropClient()
feedback_client = FeedbackClient()

class CreateSessionRequest(BaseModel):
    user_id: str
    locale: str
    consent: Dict[str, Any]

class MessageRequest(BaseModel):
    user_id: str
    text: str
    images: Optional[List[str]] = []
    locale: str
    consent: Dict[str, Any]

class MessageResponse(BaseModel):
    reply_text: str
    agrollm_response: Dict[str, Any]
    flags: Dict[str, bool]
    session_state: Dict[str, Any]

@router.post("/v1/sessions")
async def create_session(request: CreateSessionRequest):
    session_id = session_store.create_session(request.user_id, request.locale, request.consent)
    return {"session_id": session_id}

@router.post("/v1/sessions/{session_id}/message", response_model=MessageResponse)
async def send_message(session_id: str, request: MessageRequest, background_tasks: BackgroundTasks):
    # 1. Normalize Request & Load Session
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Extract Context
    context = {}
    if request.images:
        context['image_analysis'] = image_client.analyze_images(request.images)
    
    context.update(geo_client.get_context(request.user_id))
    context.update(temporal_client.get_context(request.user_id))
    
    # 3. Build Prompt
    prompt_payload = prompt_manager.build_prompt(session, request.text, context)
    
    # 4. Call Model Orchestrator -> AgroLLM
    agrollm_response = agrollm_client.generate_response(prompt_payload)
    
    # 5. Apply Dialog Policy
    action = dialog_policy.determine_action(request.text, agrollm_response, session.dict())
    
    reply_text = agrollm_response.get("content", "")
    
    # Handle Dialog Policy Actions
    if action['action'] == 'human_handoff':
        reply_text = "I am forwarding this to a human expert for review."
    elif action['action'] == 'fallback':
        reply_text = action.get('response', reply_text)
    elif action['action'] == 'confirm_risk':
        reply_text = safety_ui.format_confirmation(action.get('details', 'risky action'), "Potential safety risk")
    
    # 6. Apply Safety UI Layer
    reply_text = safety_ui.sanitize_response(reply_text)
    
    # 7. Update Session Memory
    session_store.add_message(session_id, "user", request.text)
    session_store.add_message(session_id, "assistant", reply_text)
    
    # 8. Emit Feedback Events
    background_tasks.add_task(feedback_client.emit_event, "message_processed", {
        "session_id": session_id,
        "user_id": request.user_id,
        "consent": request.consent
    })
    
    return {
        "reply_text": reply_text,
        "agrollm_response": agrollm_response,
        "flags": agrollm_response.get("flags", {}),
        "session_state": session.dict()
    }
