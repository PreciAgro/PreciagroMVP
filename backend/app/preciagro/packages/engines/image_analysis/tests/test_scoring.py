from preciagro.packages.engines.image_analysis.app.services.scoring import compute_health_score


def test_compute_health_score_penalizes_lesion() -> None:
    score = compute_health_score(disease_confidence=0.9, lesion_pct=0.5, quality_passed=True)
    assert score == 0.45


def test_compute_health_score_penalizes_quality_failure() -> None:
    score = compute_health_score(disease_confidence=0.8, lesion_pct=None, quality_passed=False)
    assert score == 0.68
