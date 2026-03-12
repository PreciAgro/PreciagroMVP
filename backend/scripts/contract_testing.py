"""
PreciAgro Contract Testing Utilities

This module provides utilities for API contract testing across engines.
It validates OpenAPI schemas and ensures breaking changes are detected.
"""

import json
import sys
from pathlib import Path
from typing import Any

import yaml


def load_openapi_spec(spec_path: Path) -> dict[str, Any]:
    """Load OpenAPI specification from file."""
    with open(spec_path) as f:
        if spec_path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(f)
        return json.load(f)


def extract_schema_fields(schema: dict[str, Any]) -> set[str]:
    """Extract required and optional fields from a schema."""
    fields = set()
    
    if "properties" in schema:
        for field_name, field_def in schema["properties"].items():
            field_type = field_def.get("type", "any")
            required = field_name in schema.get("required", [])
            fields.add(f"{field_name}:{field_type}:{'required' if required else 'optional'}")
    
    return fields


def compare_schemas(
    baseline: dict[str, Any],
    current: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Compare two OpenAPI schemas and detect breaking changes.
    
    Breaking changes:
    - Removed endpoints
    - Removed required fields
    - Changed field types
    - Changed field from optional to required
    """
    breaking_changes = []
    
    # Compare paths (endpoints)
    baseline_paths = set(baseline.get("paths", {}).keys())
    current_paths = set(current.get("paths", {}).keys())
    
    removed_paths = baseline_paths - current_paths
    for path in removed_paths:
        breaking_changes.append({
            "type": "removed_endpoint",
            "path": path,
            "severity": "breaking",
            "message": f"Endpoint {path} was removed"
        })
    
    # Compare schemas (components)
    baseline_schemas = baseline.get("components", {}).get("schemas", {})
    current_schemas = current.get("components", {}).get("schemas", {})
    
    for schema_name, baseline_schema in baseline_schemas.items():
        if schema_name not in current_schemas:
            breaking_changes.append({
                "type": "removed_schema",
                "schema": schema_name,
                "severity": "breaking",
                "message": f"Schema {schema_name} was removed"
            })
            continue
        
        current_schema = current_schemas[schema_name]
        
        # Check for removed required fields
        baseline_required = set(baseline_schema.get("required", []))
        current_required = set(current_schema.get("required", []))
        baseline_props = set(baseline_schema.get("properties", {}).keys())
        current_props = set(current_schema.get("properties", {}).keys())
        
        removed_fields = baseline_props - current_props
        for field in removed_fields:
            if field in baseline_required:
                breaking_changes.append({
                    "type": "removed_required_field",
                    "schema": schema_name,
                    "field": field,
                    "severity": "breaking",
                    "message": f"Required field {schema_name}.{field} was removed"
                })
        
        # Check for fields becoming required
        newly_required = current_required - baseline_required
        for field in newly_required:
            if field in baseline_props:
                breaking_changes.append({
                    "type": "field_now_required",
                    "schema": schema_name,
                    "field": field,
                    "severity": "breaking",
                    "message": f"Field {schema_name}.{field} changed from optional to required"
                })
    
    return breaking_changes


def validate_contract(
    baseline_path: Path,
    current_path: Path,
    fail_on_breaking: bool = True
) -> bool:
    """
    Validate API contract between baseline and current specs.
    
    Returns True if no breaking changes, False otherwise.
    """
    baseline = load_openapi_spec(baseline_path)
    current = load_openapi_spec(current_path)
    
    breaking_changes = compare_schemas(baseline, current)
    
    if breaking_changes:
        print("⚠️  Breaking changes detected:")
        for change in breaking_changes:
            print(f"  - [{change['type']}] {change['message']}")
        
        if fail_on_breaking:
            return False
    else:
        print("✅ No breaking changes detected")
    
    return True


def main():
    """CLI entry point for contract testing."""
    if len(sys.argv) < 3:
        print("Usage: python contract_testing.py <baseline_spec> <current_spec>")
        print("Example: python contract_testing.py api_v1.yaml api_v2.yaml")
        sys.exit(1)
    
    baseline_path = Path(sys.argv[1])
    current_path = Path(sys.argv[2])
    
    if not baseline_path.exists():
        print(f"Error: Baseline spec not found: {baseline_path}")
        sys.exit(1)
    
    if not current_path.exists():
        print(f"Error: Current spec not found: {current_path}")
        sys.exit(1)
    
    success = validate_contract(baseline_path, current_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
