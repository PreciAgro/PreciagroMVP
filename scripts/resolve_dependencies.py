"""
PreciAgro Engine Dependency Resolver

Resolves which engines need testing based on changed files
using the engine dependency graph.
"""

import sys
from pathlib import Path
from typing import Set

import yaml


def load_dependency_graph(graph_path: Path) -> dict:
    """Load the engine dependency graph."""
    with open(graph_path) as f:
        return yaml.safe_load(f)


def get_affected_engines(
    changed_files: list[str],
    dependency_graph: dict
) -> Set[str]:
    """
    Determine which engines are affected by the changed files.
    
    Returns both directly changed engines AND their downstream dependents.
    """
    affected = set()
    
    # Map paths to engines
    engine_paths = {
        f"preciagro/packages/engines/{engine}/": engine
        for engine in dependency_graph.keys()
        if engine != "shared"
    }
    
    # Check for shared library changes
    shared_changed = any(
        "preciagro/packages/shared/" in f for f in changed_files
    )
    
    if shared_changed:
        # ALL engines affected if shared libs change
        return set(dependency_graph.keys()) - {"shared"}
    
    # Find directly changed engines
    directly_changed = set()
    for file_path in changed_files:
        for engine_path, engine_name in engine_paths.items():
            if file_path.startswith(engine_path):
                directly_changed.add(engine_name)
                break
    
    # Check for schema changes
    schema_changed = any("schemas/" in f for f in changed_files)
    
    if schema_changed:
        # Find which engines use the changed schemas
        for file_path in changed_files:
            if "schemas/" not in file_path:
                continue
            schema_file = Path(file_path).name
            
            for engine, config in dependency_graph.items():
                if engine == "shared":
                    continue
                schemas = config.get("shared_schemas", [])
                for schema_pattern in schemas:
                    if schema_file in schema_pattern or "*" in schema_pattern:
                        directly_changed.add(engine)
    
    # Add downstream dependents (cascading)
    affected = set(directly_changed)
    
    def add_dependents(engine: str, visited: Set[str]):
        """Recursively add downstream dependents."""
        if engine in visited:
            return
        visited.add(engine)
        
        config = dependency_graph.get(engine, {})
        triggers = config.get("triggers", [])
        
        if triggers == ["ALL"]:
            # This is shared - affects everything
            affected.update(dependency_graph.keys() - {"shared"})
            return
        
        for triggered_engine in triggers:
            affected.add(triggered_engine)
            add_dependents(triggered_engine, visited)
    
    visited = set()
    for engine in directly_changed:
        add_dependents(engine, visited)
    
    return affected


def main():
    """CLI entry point for CI integration."""
    
    # Default paths
    graph_path = Path(".github/engine_dependencies.yml")
    
    if not graph_path.exists():
        print("ENGINE_DEPENDENCIES_NOT_FOUND")
        print("Falling back to all engines")
        sys.exit(0)
    
    # Read changed files from stdin or args
    if len(sys.argv) > 1:
        changed_files = sys.argv[1:]
    else:
        changed_files = [line.strip() for line in sys.stdin if line.strip()]
    
    if not changed_files:
        print("NO_CHANGED_FILES")
        sys.exit(0)
    
    # Load graph and resolve
    graph = load_dependency_graph(graph_path)
    affected = get_affected_engines(changed_files, graph)
    
    print("=== Dependency Resolution ===")
    print(f"Changed files: {len(changed_files)}")
    print(f"Affected engines: {len(affected)}")
    print()
    print("Engines to test:")
    for engine in sorted(affected):
        print(f"  - {engine}")
    
    # Output for CI (space-separated)
    print()
    print(f"::set-output name=engines::{' '.join(sorted(affected))}")
    
    # Also output as JSON for matrix
    import json
    engine_matrix = [{"name": e, "path": f"preciagro/packages/engines/{e}"} for e in sorted(affected)]
    print(f"::set-output name=matrix::{json.dumps(engine_matrix)}")


if __name__ == "__main__":
    main()
