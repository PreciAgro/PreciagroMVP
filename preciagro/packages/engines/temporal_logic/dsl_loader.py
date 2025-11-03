"""YAML DSL loader for temporal rules."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .contracts import Action, Condition, RuleCreate, WindowConfig

logger = logging.getLogger(__name__)


class DSLLoader:
    """Loads temporal rules from YAML DSL files."""

    def __init__(self, rules_dir: Optional[str] = None):
        """Initialize DSL loader."""
        self.rules_dir = (
            Path(rules_dir) if rules_dir else Path(__file__).parent / "rules"
        )

    async def load_rules(self) -> List[Dict[str, Any]]:
        """Asynchronously load raw rule dictionaries."""
        yaml_files = list(self.rules_dir.glob("*.yaml"))
        if not yaml_files:
            yaml_files = [self.rules_dir / "temporal_rules.yaml"]

        rules: List[Dict[str, Any]] = []

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    yaml_content = yaml.safe_load(f) or {}
            except FileNotFoundError:
                continue

            for rule_data in yaml_content.get("rules", []):
                if self._validate_rule(rule_data):
                    rules.append(rule_data)

        return rules

    def load_rules_from_file(self, file_path: str) -> List[RuleCreate]:
        """Load rules from a specific YAML file."""
        try:
            file_path = Path(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                yaml_content = yaml.safe_load(f)

            return self._parse_yaml_rules(yaml_content)

        except Exception as e:
            logger.error(f"Error loading rules from {file_path}: {e}")
            raise

    def load_all_rules(self) -> List[RuleCreate]:
        """Load all rules from the rules directory."""
        rules = []

        if not self.rules_dir.exists():
            logger.warning(f"Rules directory not found: {self.rules_dir}")
            return rules

        for yaml_file in self.rules_dir.glob("*.yaml"):
            try:
                file_rules = self.load_rules_from_file(yaml_file)
                rules.extend(file_rules)
                logger.info(f"Loaded {len(file_rules)} rules from {yaml_file.name}")
            except Exception as e:
                logger.error(f"Failed to load rules from {yaml_file}: {e}")

        return rules

    def _validate_rule(self, rule_data: Dict[str, Any]) -> bool:
        """Basic validation for rule dictionaries."""
        if not isinstance(rule_data, dict):
            return False
        return bool(rule_data.get("conditions")) and bool(rule_data.get("actions"))

    def _parse_yaml_rules(self, yaml_content: Dict[str, Any]) -> List[RuleCreate]:
        """Parse YAML content into Rule objects."""
        rules = []

        if "rules" not in yaml_content:
            raise ValueError("YAML must contain 'rules' key")

        for rule_data in yaml_content["rules"]:
            try:
                rule = self._parse_single_rule(rule_data)
                rules.append(rule)
            except Exception as e:
                logger.error(
                    f"Error parsing rule {rule_data.get('name', 'unknown')}: {e}"
                )
                raise

        return rules

    def _parse_single_rule(self, rule_data: Dict[str, Any]) -> RuleCreate:
        """Parse a single rule from YAML data."""
        # Parse conditions
        conditions = []
        for cond_data in rule_data.get("conditions", []):
            condition = Condition(
                field=cond_data["field"],
                operator=cond_data["operator"],
                value=cond_data["value"],
                weight=cond_data.get("weight", 1.0),
            )
            conditions.append(condition)

        # Parse actions
        actions = []
        for action_data in rule_data.get("actions", []):
            action = Action(
                type=action_data["type"],
                config=action_data["config"],
                delay=action_data.get("delay", 0),
                channel=action_data.get("channel"),
            )
            actions.append(action)

        # Parse window configuration
        window_data = rule_data.get("window", {})
        window_config = WindowConfig(
            type=window_data.get("type", "sliding"),
            size=window_data.get("size", 3600),  # default 1 hour
            advance=window_data.get("advance"),
            session_timeout=window_data.get("session_timeout"),
        )

        return RuleCreate(
            name=rule_data["name"],
            description=rule_data.get("description"),
            conditions=conditions,
            actions=actions,
            window_config=window_config,
            enabled=rule_data.get("enabled", True),
        )

    def validate_yaml_schema(self, yaml_content: Dict[str, Any]) -> List[str]:
        """Validate YAML schema and return list of errors."""
        errors = []

        # Check top-level structure
        if "rules" not in yaml_content:
            errors.append("Missing 'rules' key at root level")
            return errors

        if not isinstance(yaml_content["rules"], list):
            errors.append("'rules' must be a list")
            return errors

        # Validate each rule
        for i, rule in enumerate(yaml_content["rules"]):
            rule_errors = self._validate_rule_schema(rule, f"rules[{i}]")
            errors.extend(rule_errors)

        return errors

    def _validate_rule_schema(self, rule: Dict[str, Any], path: str) -> List[str]:
        """Validate a single rule's schema."""
        errors = []

        # Required fields
        required_fields = ["name", "conditions", "actions"]
        for field in required_fields:
            if field not in rule:
                errors.append(f"{path}: Missing required field '{field}'")

        # Validate conditions
        if "conditions" in rule:
            if not isinstance(rule["conditions"], list):
                errors.append(f"{path}.conditions: Must be a list")
            else:
                for i, cond in enumerate(rule["conditions"]):
                    cond_errors = self._validate_condition_schema(
                        cond, f"{path}.conditions[{i}]"
                    )
                    errors.extend(cond_errors)

        # Validate actions
        if "actions" in rule:
            if not isinstance(rule["actions"], list):
                errors.append(f"{path}.actions: Must be a list")
            else:
                for i, action in enumerate(rule["actions"]):
                    action_errors = self._validate_action_schema(
                        action, f"{path}.actions[{i}]"
                    )
                    errors.extend(action_errors)

        # Validate window config
        if "window" in rule:
            window_errors = self._validate_window_schema(
                rule["window"], f"{path}.window"
            )
            errors.extend(window_errors)

        return errors

    def _validate_condition_schema(
        self, condition: Dict[str, Any], path: str
    ) -> List[str]:
        """Validate condition schema."""
        errors = []

        required_fields = ["field", "operator", "value"]
        for field in required_fields:
            if field not in condition:
                errors.append(f"{path}: Missing required field '{field}'")

        # Validate operator
        valid_operators = [
            "eq",
            "ne",
            "gt",
            "gte",
            "lt",
            "lte",
            "in",
            "not_in",
            "contains",
            "exists",
        ]
        if "operator" in condition and condition["operator"] not in valid_operators:
            errors.append(
                f"{path}.operator: Invalid operator '{condition['operator']}'"
            )

        return errors

    def _validate_action_schema(self, action: Dict[str, Any], path: str) -> List[str]:
        """Validate action schema."""
        errors = []

        required_fields = ["type", "config"]
        for field in required_fields:
            if field not in action:
                errors.append(f"{path}: Missing required field '{field}'")

        # Validate action type
        valid_types = ["message", "webhook", "schedule", "alert"]
        if "type" in action and action["type"] not in valid_types:
            errors.append(f"{path}.type: Invalid action type '{action['type']}'")

        return errors

    def _validate_window_schema(self, window: Dict[str, Any], path: str) -> List[str]:
        """Validate window configuration schema."""
        errors = []

        # Validate window type
        valid_types = ["sliding", "tumbling", "session"]
        if "type" in window and window["type"] not in valid_types:
            errors.append(f"{path}.type: Invalid window type '{window['type']}'")

        # Validate size
        if "size" in window:
            if not isinstance(window["size"], int) or window["size"] <= 0:
                errors.append(f"{path}.size: Must be a positive integer")

        return errors


def create_sample_yaml() -> str:
    """Create a sample YAML rules file content."""
    return """
# Temporal Logic Rules Configuration
version: "1.0"
metadata:
  description: "Sample temporal rules for agricultural monitoring"
  created_by: "PreciAgro System"

rules:
  - name: "pest_detection_alert"
    description: "Send immediate alert when pest is detected"
    enabled: true
    conditions:
      - field: "event_type"
        operator: "eq"
        value: "pest_detection"
        weight: 1.0
      - field: "payload.confidence"
        operator: "gte"
        value: 0.8
        weight: 0.8
    actions:
      - type: "message"
        channel: "whatsapp"
        config:
          template_id: "pest_alert"
          recipient: "{{event.metadata.farm_owner}}"
          template_params:
            pest_type: "{{event.payload.pest_type}}"
            location: "{{event.payload.location}}"
            confidence: "{{event.payload.confidence}}"
        delay: 0
    window:
      type: "tumbling"
      size: 300  # 5 minutes

  - name: "irrigation_reminder"
    description: "Send irrigation reminder based on weather and soil conditions"
    enabled: true
    conditions:
      - field: "event_type"
        operator: "in"
        value: ["weather_update", "sensor_reading"]
        weight: 1.0
      - field: "payload.soil_moisture"
        operator: "lt"
        value: 30
        weight: 1.0
      - field: "payload.weather.precipitation_probability"
        operator: "lt"
        value: 0.3
        weight: 0.7
    actions:
      - type: "message"
        channel: "sms"
        config:
          message: "🌱 Irrigation needed! Soil moisture is {{payload.soil_moisture}}% and low rain chance."
          recipient: "{{metadata.farmer_phone}}"
        delay: 1800  # 30 minutes delay
    window:
      type: "sliding"
      size: 3600  # 1 hour
      advance: 900  # 15 minutes

  - name: "disease_progression_tracking"
    description: "Track disease progression over time"
    enabled: true
    conditions:
      - field: "event_type"
        operator: "eq"
        value: "disease_detection"
        weight: 1.0
    actions:
      - type: "webhook"
        config:
          webhook_url: "https://api.preciagro.com/disease-tracking"
          webhook_payload:
            disease_id: "{{payload.disease_id}}"
            severity: "{{payload.severity}}"
            location: "{{payload.location}}"
            timestamp: "{{timestamp}}"
        delay: 0
      - type: "schedule"
        config:
          task_type: "follow_up_check"
          schedule_after: 86400  # 24 hours
          params:
            location: "{{payload.location}}"
            disease_id: "{{payload.disease_id}}"
        delay: 0
    window:
      type: "session"
      session_timeout: 7200  # 2 hours
"""


# Utility function to save sample YAML
def save_sample_rules(file_path: str = None) -> None:
    """Save sample rules to a file."""
    if file_path is None:
        file_path = Path(__file__).parent / "rules" / "temporal_rules.yaml"

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(create_sample_yaml())

    logger.info(f"Sample rules saved to {file_path}")


if __name__ == "__main__":
    # Create sample rules file when run directly
    save_sample_rules()
