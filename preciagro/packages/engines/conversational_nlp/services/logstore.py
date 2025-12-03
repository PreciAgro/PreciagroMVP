"""Persistent conversation log store (JSONL on disk)."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from ..models import ChatMessageRequest, ChatMessageResponse, SessionContext, ToolsContext
from .redaction import sanitize_payload


class ConversationLogStore:
    """Writes conversation turns to a JSONL file for offline analysis."""

    def __init__(
        self,
        path: Optional[str],
        *,
        retention_days: int,
        anonymize: bool,
        history_enabled: bool,
    ) -> None:
        self.path = Path(path) if path else None
        self.retention_days = retention_days
        self.anonymize = anonymize
        self.history_enabled = history_enabled
        self._last_cleanup = 0.0

    async def persist_turn(
        self,
        request: ChatMessageRequest,
        response: ChatMessageResponse,
        session_context: SessionContext,
        tools_context: ToolsContext,
        stage_latencies: Dict[str, int],
    ) -> None:
        if not self.path:
            return
        record = {
            "timestamp": time.time(),
            "message_id": request.message_id,
            "session_id": request.session_id,
            "tenant_id": request.tenant_id,
            "farm_id": request.farm_id,
            "user_id": request.user_id,
            "channel": request.channel,
            "intent": response.intent,
            "entities": response.entities.model_dump(),
            "answer_summary": response.answer.summary,
            "steps": response.answer.steps,
            "tool_calls": [call.model_dump() for call in response.tool_calls],
            "tools_context": tools_context.as_dict(),
            "stage_latencies_ms": stage_latencies,
            "fallback_used": response.fallback_used,
            "rag_used": response.rag_used,
            "status": response.answer.status,
            "errors": [err.model_dump() for err in response.errors],
            "versions": response.versions.model_dump(),
            "feedback": request.feedback,
            "request_sanitized": sanitize_payload(request.model_dump()),
            "session_turns": [turn.model_dump() for turn in session_context.turns] if self.history_enabled else [],
        }
        if self.anonymize:
            record["user_id"] = "<anonymized>"
            record["request_sanitized"]["user"] = "<redacted>"
        line = json.dumps(record, ensure_ascii=True)
        await asyncio.to_thread(self._append_line, line)
        await self._maybe_cleanup()

    def _append_line(self, line: str) -> None:
        assert self.path is not None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")

    async def _maybe_cleanup(self) -> None:
        if not self.path or self.retention_days <= 0:
            return
        now = time.time()
        if now - self._last_cleanup < 86400:
            return
        self._last_cleanup = now
        cutoff = now - (self.retention_days * 86400)
        await asyncio.to_thread(self._cleanup_file, cutoff)

    def _cleanup_file(self, cutoff_ts: float) -> None:
        assert self.path is not None
        if not self.path.exists():
            return
        retained_lines: List[str] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    data = json.loads(line)
                    if data.get("timestamp", 0) >= cutoff_ts:
                        retained_lines.append(line.rstrip("\n"))
                except json.JSONDecodeError:
                    continue
        with self.path.open("w", encoding="utf-8") as handle:
            for line in retained_lines:
                handle.write(f"{line}\n")
