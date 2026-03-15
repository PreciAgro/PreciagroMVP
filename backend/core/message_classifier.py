"""
Classifies incoming WhatsApp messages by type.
No external dependencies — safe to import in tests without env vars.
"""


def classify_message(num_media: int, content_type: str, body: str) -> str:
    """Return IMAGE, VOICE, TEXT, or UNKNOWN."""
    if num_media > 0 and content_type.startswith("image/"):
        return "IMAGE"
    elif num_media > 0 and content_type.startswith("audio/"):
        return "VOICE"
    elif body and body.strip():
        return "TEXT"
    return "UNKNOWN"