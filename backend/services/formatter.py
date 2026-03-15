"""
WhatsApp response formatter.
Transforms a structured diagnosis dict into a WhatsApp-ready text message.
"""

_ERROR_FALLBACK = (
    "I couldn't process that right now. This can happen when "
    "photos are very blurry or our system is busy.\n\n"
    "Please try again in a moment. If the problem continues, "
    "try sending a clearer photo or typing your question instead."
)

_REQUIRED_KEYS = {"insight", "action", "confidence", "confidence_reason", "urgency"}


def format_diagnosis(diagnosis: dict) -> str:
    """Return a WhatsApp-formatted string from a structured diagnosis dict."""
    if not diagnosis or not _REQUIRED_KEYS.issubset(diagnosis.keys()):
        return _ERROR_FALLBACK

    confidence = float(diagnosis.get("confidence", 0.0))
    urgency = diagnosis.get("urgency", "low")

    if urgency == "critical":
        return _critical_template(diagnosis, confidence)
    elif confidence < 0.60:
        return _low_confidence_template(diagnosis, confidence)
    else:
        return _standard_template(diagnosis, confidence)


def _pct(confidence: float) -> int:
    return int(round(confidence * 100))


def _standard_template(d: dict, confidence: float) -> str:
    return (
        f"🔍 *Insight*\n"
        f"{d['insight']}\n\n"
        f"⚡ *Action*\n"
        f"{d['action']}\n\n"
        f"📊 *Confidence: {_pct(confidence)}%*\n"
        f"{d['confidence_reason']}\n\n"
        f"→ Reply with another photo or question anytime."
    )


def _critical_template(d: dict, confidence: float) -> str:
    return (
        f"⚠️ *URGENT — ACT TODAY*\n\n"
        f"⚡ *Action*\n"
        f"{d['action']}\n\n"
        f"🔍 *Why*\n"
        f"{d['insight']}\n\n"
        f"📊 *Confidence: {_pct(confidence)}%*\n"
        f"{d['confidence_reason']}"
    )


def _low_confidence_template(d: dict, confidence: float) -> str:
    return (
        f"🔍 *Observation*\n"
        f"{d['insight']}\n\n"
        f"❓ *I need more information*\n"
        f"{d['follow_up']}\n\n"
        f"📊 *Confidence: {_pct(confidence)}% — too low for a recommendation*\n\n"
        f"→ Send a closer photo or describe what you're seeing."
    )
