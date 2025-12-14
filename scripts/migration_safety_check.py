"""
PreciAgro Migration Safety Check

Validates database migrations before deployment to prevent data loss
and ensure backward compatibility.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


class MigrationRisk:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Keywords that indicate breaking changes
BREAKING_KEYWORDS = {
    "drop table": MigrationRisk.CRITICAL,
    "drop column": MigrationRisk.CRITICAL,
    "delete from": MigrationRisk.CRITICAL,
    "truncate": MigrationRisk.CRITICAL,
    "alter column.*type": MigrationRisk.HIGH,
    "alter column.*not null": MigrationRisk.HIGH,
    "rename column": MigrationRisk.HIGH,
    "rename table": MigrationRisk.HIGH,
    "drop constraint": MigrationRisk.MEDIUM,
    "drop index": MigrationRisk.MEDIUM,
    "alter column.*default": MigrationRisk.LOW,
    "add column": MigrationRisk.LOW,
    "create index": MigrationRisk.LOW,
    "create table": MigrationRisk.LOW,
}

# Engines with critical data
CRITICAL_DATA_ENGINES = [
    "farm_inventory",
    "farmer_profile",
    "feedback_learning",
    "security_access",
]


def analyze_migration_file(file_path: Path) -> dict[str, Any]:
    """Analyze a migration file for potential risks."""
    
    content = file_path.read_text().lower()
    
    risks = []
    highest_risk = MigrationRisk.LOW
    
    for pattern, risk_level in BREAKING_KEYWORDS.items():
        if re.search(pattern, content, re.IGNORECASE):
            risks.append({
                "pattern": pattern,
                "risk": risk_level,
                "line": find_line_number(content, pattern)
            })
            
            # Track highest risk
            risk_order = [MigrationRisk.LOW, MigrationRisk.MEDIUM, 
                         MigrationRisk.HIGH, MigrationRisk.CRITICAL]
            if risk_order.index(risk_level) > risk_order.index(highest_risk):
                highest_risk = risk_level
    
    return {
        "file": str(file_path),
        "risks": risks,
        "highest_risk": highest_risk,
        "is_breaking": highest_risk in [MigrationRisk.HIGH, MigrationRisk.CRITICAL]
    }


def find_line_number(content: str, pattern: str) -> int:
    """Find line number where pattern occurs."""
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        if re.search(pattern, line, re.IGNORECASE):
            return i
    return -1


def check_backward_compatibility(migration_path: Path) -> dict[str, Any]:
    """Check if migration is backward compatible."""
    
    result = {
        "backward_compatible": True,
        "issues": []
    }
    
    content = migration_path.read_text()
    
    # Check for downgrade function
    if "def downgrade" not in content:
        result["backward_compatible"] = False
        result["issues"].append("Missing downgrade() function")
    elif "pass" in content.split("def downgrade")[1].split("def")[0]:
        result["backward_compatible"] = False
        result["issues"].append("downgrade() is a no-op (just pass)")
    
    # Check for data migration with no rollback
    if "execute(" in content and "op.execute" in content:
        downgrade_section = content.split("def downgrade")[1] if "def downgrade" in content else ""
        if "execute(" not in downgrade_section:
            result["issues"].append("Data migration in upgrade() but no rollback in downgrade()")
    
    return result


def check_affected_engines(migration_path: Path) -> list[str]:
    """Determine which engines are affected by this migration."""
    
    affected = []
    content = migration_path.read_text().lower()
    
    # Engine-to-table mapping
    engine_tables = {
        "farm_inventory": ["farms", "inventory", "stock", "equipment"],
        "farmer_profile": ["farmers", "profiles", "users"],
        "feedback_learning": ["feedback", "learning_signals", "audit_traces"],
        "security_access": ["permissions", "roles", "tokens", "sessions"],
        "crop_intelligence": ["crops", "recommendations", "alerts"],
        "geo_context": ["regions", "locations", "soil_data"],
    }
    
    for engine, tables in engine_tables.items():
        for table in tables:
            if table in content:
                if engine not in affected:
                    affected.append(engine)
    
    return affected


def validate_migration(migration_dir: Path) -> dict[str, Any]:
    """Validate all pending migrations."""
    
    results = {
        "migrations_checked": 0,
        "breaking_changes": [],
        "critical_engines_affected": [],
        "recommendation": "PROCEED",
        "details": []
    }
    
    # Find all migration files
    migration_files = list(migration_dir.glob("*.py"))
    
    for mig_file in migration_files:
        if mig_file.name.startswith("__"):
            continue
            
        results["migrations_checked"] += 1
        
        # Analyze file
        analysis = analyze_migration_file(mig_file)
        compat = check_backward_compatibility(mig_file)
        affected = check_affected_engines(mig_file)
        
        detail = {
            "file": mig_file.name,
            "risk": analysis["highest_risk"],
            "is_breaking": analysis["is_breaking"],
            "risks": analysis["risks"],
            "backward_compatible": compat["backward_compatible"],
            "compat_issues": compat["issues"],
            "affected_engines": affected
        }
        
        results["details"].append(detail)
        
        if analysis["is_breaking"]:
            results["breaking_changes"].append(mig_file.name)
            
        for engine in affected:
            if engine in CRITICAL_DATA_ENGINES:
                if engine not in results["critical_engines_affected"]:
                    results["critical_engines_affected"].append(engine)
    
    # Determine recommendation
    if results["breaking_changes"]:
        if results["critical_engines_affected"]:
            results["recommendation"] = "BLOCK_DEPLOY"
            results["reason"] = "Breaking changes affect critical data engines"
        else:
            results["recommendation"] = "MANUAL_APPROVAL"
            results["reason"] = "Breaking changes detected, require manual review"
    elif results["critical_engines_affected"]:
        results["recommendation"] = "EXTENDED_STAGING"
        results["reason"] = "Changes affect critical data engines"
    
    return results


def main():
    """CLI entry point."""
    
    migration_dir = Path("alembic/versions")
    if len(sys.argv) > 1:
        migration_dir = Path(sys.argv[1])
    
    if not migration_dir.exists():
        print(f"Migration directory not found: {migration_dir}")
        sys.exit(0)  # Not an error if no migrations
    
    results = validate_migration(migration_dir)
    
    print("\n" + "=" * 60)
    print("📊 Migration Safety Check Report")
    print("=" * 60)
    print(f"\nMigrations checked: {results['migrations_checked']}")
    print(f"Breaking changes: {len(results['breaking_changes'])}")
    print(f"Critical engines affected: {results['critical_engines_affected']}")
    print(f"\n🎯 Recommendation: {results['recommendation']}")
    
    if results.get("reason"):
        print(f"   Reason: {results['reason']}")
    
    if results["details"]:
        print("\n📋 Details:")
        for detail in results["details"]:
            emoji = "🔴" if detail["is_breaking"] else "🟢"
            print(f"\n{emoji} {detail['file']}")
            print(f"   Risk: {detail['risk']}")
            print(f"   Backward compatible: {detail['backward_compatible']}")
            if detail["affected_engines"]:
                print(f"   Affected engines: {', '.join(detail['affected_engines'])}")
            for risk in detail["risks"]:
                print(f"   ⚠️  Line {risk['line']}: {risk['pattern']}")
    
    # Exit with error if blocking
    if results["recommendation"] == "BLOCK_DEPLOY":
        print("\n❌ Auto-deployment blocked. Manual approval required.")
        sys.exit(1)
    elif results["recommendation"] == "MANUAL_APPROVAL":
        print("\n⚠️  Manual approval required before production deploy.")
        # Don't exit with error, but set output for CI
        print("::set-output name=requires_approval::true")
    else:
        print("\n✅ Safe to proceed with deployment.")


if __name__ == "__main__":
    main()
