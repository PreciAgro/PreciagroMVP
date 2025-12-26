"""Local Intelligence Adapter - Region-specific rules and intelligence."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LocalRule:
    """Local rule for region/crop."""

    region_code: str
    crop_variety: Optional[str]
    rule_type: str  # "season", "pest", "disease", "practice"
    rule_data: Dict[str, Any]


class LocalIntelligenceAdapter:
    """Adapter for local/regional intelligence and rules."""

    def __init__(self, local_rules_dir: Optional[str] = None):
        """Initialize Local Intelligence adapter.

        Args:
            local_rules_dir: Directory containing local rules JSON files
        """
        self.local_rules_dir = (
            Path(local_rules_dir)
            if local_rules_dir
            else Path(__file__).parent.parent / "local_rules"
        )
        self.rules: List[LocalRule] = []

        # Ensure directory exists
        self.local_rules_dir.mkdir(parents=True, exist_ok=True)

        # Load rules
        self._load_rules()

        logger.info(f"LocalIntelligenceAdapter initialized with {len(self.rules)} rules")

    def _load_rules(self) -> None:
        """Load local rules from JSON files."""
        if not self.local_rules_dir.exists():
            logger.warning(f"Local rules directory does not exist: {self.local_rules_dir}")
            return

        # Load all JSON files in directory
        for rule_file in self.local_rules_dir.glob("*.json"):
            try:
                with open(rule_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for rule_data in data:
                            self.rules.append(LocalRule(**rule_data))
                    elif isinstance(data, dict):
                        self.rules.append(LocalRule(**data))
                logger.debug(f"Loaded rules from {rule_file}")
            except Exception as e:
                logger.error(f"Error loading rules from {rule_file}: {e}")

    def get_rules(self, region_code: str, crop_variety: Optional[str] = None) -> List[LocalRule]:
        """Get local rules for region and crop variety.

        Args:
            region_code: Region identifier
            crop_variety: Optional crop variety filter

        Returns:
            List of matching local rules
        """
        matching_rules = [
            rule
            for rule in self.rules
            if rule.region_code == region_code
            and (
                crop_variety is None
                or rule.crop_variety == crop_variety
                or rule.crop_variety is None
            )
        ]

        return matching_rules

    def get_context(self, region_code: str, crop_variety: Optional[str] = None) -> Dict[str, Any]:
        """Get local context for region and crop.

        Args:
            region_code: Region identifier
            crop_variety: Optional crop variety

        Returns:
            Dictionary with local context
        """
        rules = self.get_rules(region_code, crop_variety)

        context = {
            "region_code": region_code,
            "crop_variety": crop_variety,
            "rules": [{"type": rule.rule_type, "data": rule.rule_data} for rule in rules],
        }

        return context
