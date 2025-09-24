"""DSL loader for temporal rules."""
import yaml
from pathlib import Path
from typing import List
from ..contracts import Rule


class DSLLoader:
    """Loads and validates DSL rules from YAML files."""

    def __init__(self, rules_dir: str = "rules"):
        self.rules_dir = Path(rules_dir)

    def load_rules(self) -> List[Rule]:
        """Load all rules from YAML files."""
        rules = []

        for yaml_file in self.rules_dir.glob("*.yaml"):
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)

            for rule_data in data.get("rules", []):
                rule = Rule.model_validate(rule_data)
                rules.append(rule)

        return rules

    def load_rule_by_id(self, rule_id: str) -> Rule:
        """Load specific rule by ID."""
        for rule in self.load_rules():
            if rule.id == rule_id:
                return rule
        raise ValueError(f"Rule {rule_id} not found")
