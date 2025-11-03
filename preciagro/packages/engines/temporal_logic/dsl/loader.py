"""DSL loader for temporal rules."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..contracts import Rule


class AwaitableRuleList(list):
    """List-like wrapper that can also be awaited."""

    def __await__(self):
        async def _coro():
            return self

        return _coro().__await__()


class DSLLoader:
    """Loads and validates DSL rules from YAML files."""

    def __init__(self, rules_dir: Optional[str] = None):
        base_dir = Path(__file__).resolve().parent.parent
        default_dir = base_dir / "rules"
        self.rules_dir = Path(rules_dir) if rules_dir else default_dir

    def load_rules(self) -> List[Rule]:
        """Load all rules from YAML files."""
        rules: List[Rule] = []

        for yaml_file in self.rules_dir.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            for rule_data in data.get("rules", []):
                if not self._validate_rule(rule_data):
                    continue
                rule = Rule.model_validate(rule_data)
                rules.append(rule)

        return AwaitableRuleList(rules)

    def load_rule_by_id(self, rule_id: str) -> Rule:
        """Load specific rule by ID."""
        for rule in self.load_rules():
            if rule.id == rule_id:
                return rule
        raise ValueError(f"Rule {rule_id} not found")

    def _validate_rule(self, rule_data: Dict[str, Any]) -> bool:
        """Validate required keys for a rule definition."""
        if not isinstance(rule_data, dict):
            return False
        return bool(rule_data.get("conditions")) and bool(rule_data.get("actions"))
