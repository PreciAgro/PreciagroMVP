#!/usr/bin/env python3
"""Test runner for GeoContext engine MVP."""
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*50}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*50}")

    start_time = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    duration = time.time() - start_time

    print(f"Duration: {duration:.2f}s")

    if result.returncode == 0:
        print(f"✅ SUCCESS: {description}")
        if result.stdout.strip():
            print("STDOUT:")
            print(result.stdout)
    else:
        print(f"❌ FAILED: {description}")
        print("STDERR:")
        print(result.stderr)
        if result.stdout.strip():
            print("STDOUT:")
            print(result.stdout)

    return result.returncode == 0


def main():
    """Run all tests for GeoContext MVP."""
    print("🚀 GeoContext MVP Test Suite")
    print("=" * 60)

    # Change to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    print(f"Project root: {project_root}")

    tests = [
        # Syntax and import checks
        ("python -m py_compile preciagro/packages/engines/geo_context/pipeline/resolver.py",
         "Syntax check - Main resolver"),

        ("python -m py_compile preciagro/packages/engines/geo_context/api/routes/api.py",
         "Syntax check - API routes"),

        ("python -m py_compile preciagro/packages/engines/geo_context/storage/cache.py",
         "Syntax check - Cache layer"),

        # Unit tests
        ("python -m pytest preciagro/packages/engines/geo_context/tests/test_resolver_pipeline.py -v",
         "Unit tests - Resolver pipeline"),

        ("python -m pytest preciagro/packages/engines/geo_context/tests/test_api_smoke.py -v",
         "API smoke tests"),

        ("python -m pytest preciagro/packages/engines/geo_context/tests/test_golden_snapshots.py -v",
         "Golden snapshot tests"),

        # Integration tests
        ("python -c \"from preciagro.packages.engines.geo_context.pipeline.resolver import FieldContextResolver; print('✅ Resolver import successful')\"",
         "Import test - Main resolver"),

        ("python -c \"from preciagro.packages.engines.geo_context.storage.cache import get_cache; print('✅ Cache import successful')\"",
         "Import test - Cache layer"),

        ("python -c \"from preciagro.packages.engines.geo_context.telemetry.metrics import telemetry; print('✅ Telemetry import successful')\"",
         "Import test - Telemetry"),

        # Configuration validation
        ("python -c \"from preciagro.packages.engines.geo_context.config import settings; print(f'✅ Config loaded: {settings.DEBUG}')\"",
         "Configuration validation"),
    ]

    results = []
    total_start = time.time()

    for cmd, description in tests:
        success = run_command(cmd, description)
        results.append((description, success))

        if not success:
            print(f"\n⚠️  Test failed: {description}")
            print("Continuing with remaining tests...")

    total_duration = time.time() - total_start

    # Summary
    print(f"\n{'='*60}")
    print("🏁 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total duration: {total_duration:.2f}s")

    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed

    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success rate: {passed/len(results)*100:.1f}%")

    print("\nDetailed Results:")
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {description}")

    if failed > 0:
        print(f"\n⚠️  {failed} tests failed. Check output above for details.")
        return 1
    else:
        print(f"\n🎉 All {passed} tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
