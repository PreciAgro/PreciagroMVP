"""
PreciAgro License Validation Script

Validates that all project dependencies use approved open-source licenses.
Required for EU and Zimbabwe government contract compliance.
"""

import csv
import sys
from pathlib import Path


# Approved licenses for PreciAgro
APPROVED_LICENSES = {
    # Permissive licenses
    "MIT",
    "MIT License",
    "BSD",
    "BSD License",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "Apache 2.0",
    "Apache License 2.0",
    "Apache Software License",
    "Apache-2.0",
    "ISC",
    "ISC License",
    "PSF",
    "Python Software Foundation License",
    "PSFL",
    "MPL-2.0",
    "Mozilla Public License 2.0",
    "Unlicense",
    "Public Domain",
    "CC0",
    
    # Weak copyleft (acceptable for dependencies)
    "LGPL",
    "LGPL-2.1",
    "LGPL-3.0",
    "GNU Lesser General Public License",
}

# Licenses that require legal review
REVIEW_REQUIRED_LICENSES = {
    "GPL",
    "GPL-2.0",
    "GPL-3.0",
    "GNU General Public License",
    "AGPL",
    "AGPL-3.0",
}

# Licenses that are NOT approved
REJECTED_LICENSES = {
    "Commercial",
    "Proprietary",
}


def validate_licenses(csv_path: Path) -> tuple[bool, list[dict]]:
    """
    Validate licenses from pip-licenses CSV output.
    
    Returns:
        (success, issues): Tuple of success flag and list of license issues
    """
    issues = []
    
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            package = row.get("Name", "Unknown")
            license_name = row.get("License", "Unknown")
            
            # Normalize license name
            license_normalized = license_name.strip()
            
            # Check if license is approved
            if license_normalized in REJECTED_LICENSES:
                issues.append({
                    "package": package,
                    "license": license_name,
                    "status": "REJECTED",
                    "action": "Remove or replace this dependency"
                })
            elif license_normalized in REVIEW_REQUIRED_LICENSES:
                issues.append({
                    "package": package,
                    "license": license_name,
                    "status": "REVIEW_REQUIRED",
                    "action": "Legal review required before production use"
                })
            elif license_normalized not in APPROVED_LICENSES:
                # Unknown license - needs review
                issues.append({
                    "package": package,
                    "license": license_name,
                    "status": "UNKNOWN",
                    "action": "Review and add to approved list if acceptable"
                })
    
    # Success if no rejected licenses
    rejected = [i for i in issues if i["status"] == "REJECTED"]
    return len(rejected) == 0, issues


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_licenses.py <licenses.csv>")
        print("Generate with: pip-licenses --format=csv --output-file=licenses.csv")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1])
    
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)
    
    success, issues = validate_licenses(csv_path)
    
    if issues:
        print("\n📋 License Validation Report")
        print("=" * 60)
        
        for issue in issues:
            status_emoji = {
                "REJECTED": "❌",
                "REVIEW_REQUIRED": "⚠️",
                "UNKNOWN": "❓"
            }.get(issue["status"], "❓")
            
            print(f"\n{status_emoji} {issue['package']}")
            print(f"   License: {issue['license']}")
            print(f"   Status: {issue['status']}")
            print(f"   Action: {issue['action']}")
        
        print("\n" + "=" * 60)
        
        rejected_count = len([i for i in issues if i["status"] == "REJECTED"])
        review_count = len([i for i in issues if i["status"] == "REVIEW_REQUIRED"])
        unknown_count = len([i for i in issues if i["status"] == "UNKNOWN"])
        
        print(f"Summary: {rejected_count} rejected, {review_count} need review, {unknown_count} unknown")
    else:
        print("✅ All licenses are approved")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
