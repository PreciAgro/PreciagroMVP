from typing import Dict, Any


class SafetyUI:
    def __init__(self):
        pass

    def sanitize_response(self, response_text: str) -> str:
        """
        Rewrites unsafe responses into safe UX text.
        """
        # Placeholder for actual sanitization logic (regex, keyword replacement, etc.)
        # For now, just a pass-through or simple check
        if "UNSAFE" in response_text:
            return "I cannot provide that information due to safety guidelines."
        return response_text

    def format_confirmation(self, action_description: str, risks: str) -> str:
        """
        Formats a confirmation request for the user.
        """
        return f"⚠️ SAFETY CHECK: You requested to {action_description}. \n\nPotential Risks: {risks}\n\nPlease type 'CONFIRM' to proceed."

    def format_warning(self, warning_message: str) -> str:
        """
        Formats a warning message.
        """
        return f"⚠️ WARNING: {warning_message}"
