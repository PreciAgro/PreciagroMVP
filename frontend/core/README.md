# Core Intelligence Layer

This directory contains the **local intelligence logic** for Phase Zero.

## Rules (Strictly Enforced)

1. **Deterministic Logic Only**: 
   - Same input MUST yield same output.
   - No `Math.random()` usage for core decisions.

2. **No Mock APIs**:
   - Do not pretend to call a backend.
   - Do not use `fetch()` or `axios`.
   - Logic must be pure functions or state machines.

3. **No UI Components**:
   - This folder must NOT contain any React components (`.tsx`).
   - Pure TypeScript (`.ts`) only.

## Structure
- `/intelligence`: Algorithms for analyzing farm state (e.g., Risk Calculators).
- `/scenarios`: Pre-defined state conditions for demos (e.g., "Drought Scenario").
- `/models`: Types and Interfaces defining the farm ontology.
