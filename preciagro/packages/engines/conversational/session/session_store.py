from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from pydantic import BaseModel, Field

class Consent(BaseModel):
    consent_id: str
    use_for_training: bool
    granted_at: str
    scope: List[str]

class SessionMetadata(BaseModel):
    session_id: str
    user_id: str
    created_at: str
    last_used: str
    locale: str
    consent: Consent

class SessionData(BaseModel):
    metadata: SessionMetadata
    history: List[Dict[str, Any]] = Field(default_factory=list)
    pinned_facts: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)

class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}

    def create_session(self, user_id: str, locale: str, consent: Dict[str, Any]) -> str:
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        metadata = SessionMetadata(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_used=now,
            locale=locale,
            consent=Consent(**consent)
        )
        
        session = SessionData(metadata=metadata)
        self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[SessionData]:
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, updates: Dict[str, Any]):
        if session_id in self._sessions:
            session = self._sessions[session_id]
            # Update last_used
            session.metadata.last_used = datetime.utcnow().isoformat()
            
            if 'history' in updates:
                session.history = updates['history']
            if 'pinned_facts' in updates:
                session.pinned_facts.update(updates['pinned_facts'])
            if 'context' in updates:
                session.context.update(updates['context'])

    def delete_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        session = self.get_session(session_id)
        if session:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            session.history.append(message)
            session.metadata.last_used = datetime.utcnow().isoformat()
