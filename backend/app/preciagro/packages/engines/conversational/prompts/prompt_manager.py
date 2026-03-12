import os
from typing import Dict, Any, Optional
from ..session.session_store import SessionData


class PromptManager:
    def __init__(self, template_dir: str = None):
        if template_dir is None:
            # Default to the templates directory relative to this file
            self.template_dir = os.path.join(os.path.dirname(__file__), "templates")
        else:
            self.template_dir = template_dir

        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        templates = {}
        for filename in os.listdir(self.template_dir):
            if filename.endswith(".txt"):
                name = filename[:-4]
                with open(os.path.join(self.template_dir, filename), "r") as f:
                    templates[name] = f.read()
        return templates

    def build_prompt(
        self,
        session: SessionData,
        user_query: str,
        context: Dict[str, Any],
        template_name: str = "diagnosis",
    ) -> Dict[str, Any]:
        """
        Constructs the final prompt payload for AgroLLM.
        """
        template = self.templates.get(template_name)
        if not template:
            # Fallback to a default or error
            template = "Context: {context_str}\nUser: {user_query}"

        # Format context string from session and external context
        context_parts = []

        # Pinned facts
        if session.pinned_facts:
            context_parts.append("Pinned Facts:")
            for k, v in session.pinned_facts.items():
                context_parts.append(f"- {k}: {v}")

        # External context (weather, crop stage, etc.)
        if context:
            context_parts.append("\nEnvironmental Context:")
            for k, v in context.items():
                context_parts.append(f"- {k}: {v}")

        # History (simplified for prompt construction, ideally this is handled by the LLM's chat interface,
        # but here we might need to inject it if using a completion endpoint,
        # or just pass it alongside. Assuming AgroLLM takes 'messages' list,
        # but this method returns a constructed prompt structure.)

        context_str = "\n".join(context_parts)

        formatted_prompt = template.format(
            context_str=context_str, user_query=user_query, **context
        )

        # Construct the payload for AgroLLM
        payload = {
            "prompt": formatted_prompt,
            "history": session.history,  # Pass history separately if Orchestrator handles it
            "model_mode": "pretrained",  # STRICT ENFORCEMENT
            "context": context,  # Structured context
        }

        return payload
