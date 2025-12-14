"""Utility script to inspect the last N conversation turns from the JSONL log."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List


def tail_lines(path: Path, count: int) -> List[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()
    return [line.strip() for line in lines[-count:]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump the last N conversation turns.")
    parser.add_argument(
        "--log",
        default="reports/conversation_turns.jsonl",
        help="Path to the conversation JSONL log file.",
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=3,
        help="Number of turns to display.",
    )
    args = parser.parse_args()
    log_path = Path(args.log)
    lines = tail_lines(log_path, args.count)
    if not lines:
        print(f"No log lines found at {log_path}")
        return
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            print(f"[corrupt] {line}")
            continue
        summary = record.get("answer_summary") or record.get("intent")
        print(
            f"[{record.get('timestamp')}] session={record.get('session_id')} tenant={record.get('tenant_id')} "
            f"intent={record.get('intent')} status={record.get('status')} summary={summary}"
        )


if __name__ == "__main__":
    main()
