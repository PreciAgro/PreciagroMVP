from typing import List, Dict, Any
from .session_store import SessionData


class MemoryManager:
    def __init__(self, max_history_turns: int = 10, max_tokens: int = 2000):
        self.max_history_turns = max_history_turns
        self.max_tokens = max_tokens

    def get_context_window(self, session: SessionData) -> List[Dict[str, Any]]:
        """
        Retrieves the relevant context window for the current turn.
        Includes pinned facts and the last N turns.
        """
        # Start with pinned facts as system messages or context
        context_messages = []

        # Add pinned facts if available
        if session.pinned_facts:
            facts_text = "Pinned Facts:\n" + "\n".join(
                [f"{k}: {v}" for k, v in session.pinned_facts.items()]
            )
            context_messages.append({"role": "system", "content": facts_text})

        # Get recent history
        history = session.history[-self.max_history_turns :]

        # TODO: Implement token counting and trimming logic here if needed
        # For now, just taking the last N turns

        context_messages.extend(history)

        return context_messages

    def trim_history(self, session: SessionData):
        """
        Trims the session history to stay within limits.
        """
        if len(session.history) > self.max_history_turns:
            session.history = session.history[-self.max_history_turns :]
