
from preciagro.packages.shared.schemas import DiagnosisOut, LabelScore
# Very dumb placeholder. Replace with real model call later.


def diagnose(image_base64: str, crop_hint: str | None) -> DiagnosisOut:
    label = "early_blight" if (
        crop_hint or "").lower() == "tomato" else "leaf_spot"
    return DiagnosisOut(
        labels=[LabelScore(name=label, score=0.82)],
        notes="Baseline heuristic diagnosis (stub).",
        model_version="stub-0.1"
    )
