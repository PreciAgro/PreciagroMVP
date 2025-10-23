"""
Metrics Service for CIE Observability.
Tracks: stage accuracy, action acceptance, disease false-alarms, data completeness, latency.
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import json


@dataclass
class MetricValue:
    """Single metric observation."""
    timestamp: datetime
    value: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class MetricSummary:
    """Aggregated metric statistics."""
    metric_name: str
    period_start: datetime
    period_end: datetime
    count: int
    mean: float
    min: float
    max: float
    p50: float
    p95: float
    breakdown: Dict = field(default_factory=dict)


class MetricsCollector:
    """
    In-memory metrics collector (MVP - migrate to Postgres/TimescaleDB later).
    Thread-safe operations required for production.
    """

    def __init__(self):
        self.metrics: Dict[str, List[MetricValue]] = defaultdict(list)
        self.events: List[Dict] = []  # Event log for replay/debugging

    def record_metric(self, name: str, value: float, metadata: Dict = None):
        """Record a single metric observation."""
        metric = MetricValue(
            timestamp=datetime.now(),
            value=value,
            metadata=metadata or {}
        )
        self.metrics[name].append(metric)

    def record_event(self, event_type: str, data: Dict):
        """Record an event for audit trail."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }
        self.events.append(event)

    def get_metric_summary(
        self,
        name: str,
        window_hours: int = 24,
        breakdown_by: Optional[str] = None
    ) -> MetricSummary:
        """Get summary statistics for a metric over a time window."""
        cutoff = datetime.now() - timedelta(hours=window_hours)
        recent = [m for m in self.metrics.get(
            name, []) if m.timestamp >= cutoff]

        if not recent:
            return MetricSummary(
                metric_name=name,
                period_start=cutoff,
                period_end=datetime.now(),
                count=0,
                mean=0.0,
                min=0.0,
                max=0.0,
                p50=0.0,
                p95=0.0
            )

        values = sorted([m.value for m in recent])
        count = len(values)

        # Calculate percentiles
        p50_idx = int(count * 0.50)
        p95_idx = int(count * 0.95)

        summary = MetricSummary(
            metric_name=name,
            period_start=cutoff,
            period_end=datetime.now(),
            count=count,
            mean=sum(values) / count,
            min=min(values),
            max=max(values),
            p50=values[p50_idx] if count > 0 else 0.0,
            p95=values[p95_idx] if count > 0 else 0.0
        )

        # Optional breakdown
        if breakdown_by:
            breakdown = defaultdict(list)
            for m in recent:
                key = m.metadata.get(breakdown_by, "unknown")
                breakdown[key].append(m.value)

            summary.breakdown = {
                k: {
                    "count": len(v),
                    "mean": sum(v) / len(v) if v else 0.0
                }
                for k, v in breakdown.items()
            }

        return summary


# Global metrics instance (replace with proper DI in production)
_metrics = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics


# ===================================
# CIE-Specific Metric Trackers
# ===================================

def track_stage_accuracy(
    field_id: str,
    predicted_stage: str,
    ground_truth_stage: str,
    confidence: float
):
    """
    Track stage prediction accuracy.
    Ground truth comes from photo prompts with agronomist verification.
    """
    correct = 1.0 if predicted_stage == ground_truth_stage else 0.0

    _metrics.record_metric(
        "stage_accuracy",
        correct,
        metadata={
            "field_id": field_id,
            "predicted": predicted_stage,
            "actual": ground_truth_stage,
            "confidence": confidence
        }
    )

    _metrics.record_event("stage_verification", {
        "field_id": field_id,
        "predicted_stage": predicted_stage,
        "ground_truth_stage": ground_truth_stage,
        "correct": correct == 1.0,
        "confidence": confidence
    })


def track_action_decision(
    field_id: str,
    action_id: str,
    action_type: str,
    decision: str,  # "accepted", "rejected", "ignored"
    confidence: float,
    metadata: Dict = None
):
    """Track user's decision on an action recommendation."""
    acceptance_value = 1.0 if decision == "accepted" else 0.0

    _metrics.record_metric(
        "action_acceptance_overall",
        acceptance_value,
        metadata={
            "field_id": field_id,
            "action_id": action_id,
            "action_type": action_type,
            "decision": decision,
            "confidence": confidence,
            **(metadata or {})
        }
    )

    # Track by action type
    _metrics.record_metric(
        f"action_acceptance_{action_type}",
        acceptance_value,
        metadata={
            "field_id": field_id,
            "action_id": action_id,
            "confidence": confidence
        }
    )

    _metrics.record_event("action_decision", {
        "field_id": field_id,
        "action_id": action_id,
        "action_type": action_type,
        "decision": decision,
        "confidence": confidence,
        "metadata": metadata
    })


def track_disease_false_alarm(
    field_id: str,
    disease: str,
    risk_level: str,
    follow_up_observation: str,  # "symptoms_confirmed", "no_symptoms", "unknown"
    hours_since_alert: int
):
    """
    Track disease false-alarm rate.
    False alarm = "High risk" alert with no symptoms within 72h.
    """
    is_false_alarm = (
        risk_level in ["high", "critical"] and
        follow_up_observation == "no_symptoms" and
        hours_since_alert <= 72
    )

    _metrics.record_metric(
        "disease_false_alarm",
        1.0 if is_false_alarm else 0.0,
        metadata={
            "field_id": field_id,
            "disease": disease,
            "risk_level": risk_level,
            "observation": follow_up_observation,
            "hours_since_alert": hours_since_alert
        }
    )

    # Track by disease type
    _metrics.record_metric(
        f"disease_false_alarm_{disease}",
        1.0 if is_false_alarm else 0.0,
        metadata={"field_id": field_id}
    )

    _metrics.record_event("disease_verification", {
        "field_id": field_id,
        "disease": disease,
        "risk_level": risk_level,
        "observation": follow_up_observation,
        "hours_since_alert": hours_since_alert,
        "false_alarm": is_false_alarm
    })


def track_data_completeness(
    field_id: str,
    period_days: int,
    photo_count: int,
    vi_observations: int,
    weather_days_available: int,
    action_logs: int
):
    """
    Track data completeness for a field over a period.

    Expected rates:
    - Photos: 1 per 14 days
    - VI: 1 per 5-7 days (Sentinel-2)
    - Weather: daily
    - Action logs: 1 per action recommended
    """
    expected_photos = period_days / 14.0
    expected_vi = period_days / 6.0
    expected_weather = period_days

    photo_completeness = min(
        1.0, photo_count / expected_photos) if expected_photos > 0 else 0.0
    vi_completeness = min(1.0, vi_observations /
                          expected_vi) if expected_vi > 0 else 0.0
    weather_completeness = weather_days_available / \
        expected_weather if expected_weather > 0 else 0.0

    overall_completeness = (photo_completeness * 0.3 +
                            vi_completeness * 0.3 + weather_completeness * 0.4)

    _metrics.record_metric(
        "data_completeness",
        overall_completeness,
        metadata={
            "field_id": field_id,
            "period_days": period_days,
            "photo_completeness": photo_completeness,
            "vi_completeness": vi_completeness,
            "weather_completeness": weather_completeness
        }
    )

    _metrics.record_event("data_completeness_check", {
        "field_id": field_id,
        "period_days": period_days,
        "photo_count": photo_count,
        "vi_observations": vi_observations,
        "weather_days_available": weather_days_available,
        "action_logs": action_logs,
        "overall_completeness": overall_completeness
    })


def track_endpoint_latency(
    endpoint: str,
    latency_ms: float,
    status_code: int
):
    """Track API endpoint latency."""
    _metrics.record_metric(
        "endpoint_latency_ms",
        latency_ms,
        metadata={
            "endpoint": endpoint,
            "status_code": status_code
        }
    )

    # Track errors separately
    if status_code >= 400:
        _metrics.record_metric(
            "endpoint_error",
            1.0,
            metadata={
                "endpoint": endpoint,
                "status_code": status_code
            }
        )


def track_regret_proxy(
    field_id: str,
    action_id: str,
    decision: str,
    outcome_14d: Optional[str],  # "better", "worse", "neutral", "unknown"
    outcome_30d: Optional[str]
):
    """
    Track regret proxy - did ignoring/accepting action lead to better outcome?

    Regret scenarios:
    - Ignored nitrogen action → yield drop indicators
    - Ignored disease alert → symptoms appeared
    - Accepted irrigation → unnecessary (rain came)
    """
    if outcome_14d:
        regret_score = {
            "better": 0.0,    # Good decision
            "neutral": 0.2,   # Slight regret
            "worse": 1.0,     # High regret
            "unknown": 0.5    # Cannot assess
        }.get(outcome_14d, 0.5)

        _metrics.record_metric(
            "regret_proxy_14d",
            regret_score,
            metadata={
                "field_id": field_id,
                "action_id": action_id,
                "decision": decision,
                "outcome": outcome_14d
            }
        )

    if outcome_30d:
        regret_score = {
            "better": 0.0,
            "neutral": 0.2,
            "worse": 1.0,
            "unknown": 0.5
        }.get(outcome_30d, 0.5)

        _metrics.record_metric(
            "regret_proxy_30d",
            regret_score,
            metadata={
                "field_id": field_id,
                "action_id": action_id,
                "decision": decision,
                "outcome": outcome_30d
            }
        )

    _metrics.record_event("regret_assessment", {
        "field_id": field_id,
        "action_id": action_id,
        "decision": decision,
        "outcome_14d": outcome_14d,
        "outcome_30d": outcome_30d
    })


# ===================================
# Pilot Scorecard Generator
# ===================================

def generate_pilot_scorecard(window_hours: int = 168) -> Dict:
    """
    Generate weekly pilot scorecard with key metrics.

    Returns dict suitable for dashboard or Slack notification.
    """
    metrics = get_metrics_collector()

    # Stage accuracy (target: ±1 stage = 80%+)
    stage_acc = metrics.get_metric_summary("stage_accuracy", window_hours)

    # Action acceptance (target: 60%+)
    action_acc_overall = metrics.get_metric_summary(
        "action_acceptance_overall", window_hours)
    action_acc_by_type = {
        action_type: metrics.get_metric_summary(
            f"action_acceptance_{action_type}", window_hours)
        for action_type in ["nitrogen", "water", "disease", "photo_prompt"]
    }

    # Disease false-alarms (target: <15%)
    disease_false_alarm = metrics.get_metric_summary(
        "disease_false_alarm", window_hours)

    # Data completeness (target: 75%+)
    data_completeness = metrics.get_metric_summary(
        "data_completeness", window_hours)

    # Endpoint latency (target: p95 < 200ms)
    latency = metrics.get_metric_summary(
        "endpoint_latency_ms", window_hours, breakdown_by="endpoint")

    # Error rate (target: <5%)
    errors = metrics.get_metric_summary("endpoint_error", window_hours)
    error_rate = errors.mean if errors.count > 0 else 0.0

    scorecard = {
        "period": {
            "start": (datetime.now() - timedelta(hours=window_hours)).isoformat(),
            "end": datetime.now().isoformat(),
            "hours": window_hours
        },
        "stage_accuracy": {
            "mean": round(stage_acc.mean, 3),
            "count": stage_acc.count,
            "target": 0.80,
            "status": "✓" if stage_acc.mean >= 0.80 else "⚠️"
        },
        "action_acceptance": {
            "overall": {
                "mean": round(action_acc_overall.mean, 3),
                "count": action_acc_overall.count,
                "target": 0.60,
                "status": "✓" if action_acc_overall.mean >= 0.60 else "⚠️"
            },
            "by_type": {
                atype: {
                    "mean": round(summary.mean, 3),
                    "count": summary.count
                }
                for atype, summary in action_acc_by_type.items()
            }
        },
        "disease_false_alarm_rate": {
            "mean": round(disease_false_alarm.mean, 3),
            "count": disease_false_alarm.count,
            "target": 0.15,
            "status": "✓" if disease_false_alarm.mean <= 0.15 else "⚠️"
        },
        "data_completeness": {
            "mean": round(data_completeness.mean, 3),
            "count": data_completeness.count,
            "target": 0.75,
            "status": "✓" if data_completeness.mean >= 0.75 else "⚠️"
        },
        "latency_p95_ms": {
            "overall": round(latency.p95, 1),
            "by_endpoint": latency.breakdown,
            "target": 200.0,
            "status": "✓" if latency.p95 <= 200.0 else "⚠️"
        },
        "error_rate": {
            "rate": round(error_rate, 3),
            "count": errors.count,
            "target": 0.05,
            "status": "✓" if error_rate <= 0.05 else "⚠️"
        }
    }

    return scorecard


def check_policy_guardrails(scorecard: Dict) -> List[str]:
    """
    Check if metrics meet guardrails for policy rollout.
    Returns list of violations.
    """
    violations = []

    # Stage accuracy < 75%
    if scorecard["stage_accuracy"]["mean"] < 0.75:
        violations.append("stage_accuracy_low")

    # Action acceptance < 50%
    if scorecard["action_acceptance"]["overall"]["mean"] < 0.50:
        violations.append("action_acceptance_low")

    # False-alarm rate > 20%
    if scorecard["disease_false_alarm_rate"]["mean"] > 0.20:
        violations.append("disease_false_alarm_high")

    # Data completeness < 60%
    if scorecard["data_completeness"]["mean"] < 0.60:
        violations.append("data_completeness_critical")

    # Error rate > 10%
    if scorecard["error_rate"]["rate"] > 0.10:
        violations.append("error_rate_critical")

    return violations
