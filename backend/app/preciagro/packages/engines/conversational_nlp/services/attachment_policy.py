"""Attachment and input validation policies."""

from __future__ import annotations

import mimetypes
from typing import List

from ..core.config import settings
from ..models import ChatMessageRequest, ErrorCode, ErrorDetail


class AttachmentPolicy:
    """Validates inbound attachments and text limits."""

    def __init__(
        self,
        *,
        max_message_length: int,
        max_attachments: int,
        max_attachment_bytes: int,
        allowed_mime_types: List[str],
    ) -> None:
        self.max_message_length = max_message_length
        self.max_attachments = max_attachments
        self.max_attachment_bytes = max_attachment_bytes
        self.allowed_mime_types = [mime.strip().lower() for mime in allowed_mime_types]

    def validate(self, payload: ChatMessageRequest) -> List[ErrorDetail]:
        """Return policy violations."""
        errors: List[ErrorDetail] = []

        if len(payload.text or "") > self.max_message_length:
            errors.append(
                ErrorDetail(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Message exceeds {self.max_message_length} characters.",
                    component="input_policy",
                )
            )

        if len(payload.attachments) > self.max_attachments:
            errors.append(
                ErrorDetail(
                    code=ErrorCode.INVALID_ATTACHMENT,
                    message=f"Too many attachments (max {self.max_attachments}).",
                    component="input_policy",
                )
            )

        for attachment in payload.attachments:
            mime = (
                attachment.mime_type or attachment.content_type or ""
            ).lower() or self._infer_mime_from_url(attachment.url)
            if mime and mime.split(";")[0] not in self.allowed_mime_types:
                errors.append(
                    ErrorDetail(
                        code=ErrorCode.INVALID_ATTACHMENT,
                        message=f"Unsupported attachment MIME type: {mime or 'unknown'}",
                        component="input_policy",
                    )
                )
            if attachment.size_bytes and attachment.size_bytes > self.max_attachment_bytes:
                errors.append(
                    ErrorDetail(
                        code=ErrorCode.INVALID_ATTACHMENT,
                        message=(
                            f"Attachment {attachment.url or attachment.type} exceeds "
                            f"{self.max_attachment_bytes} bytes."
                        ),
                        component="input_policy",
                    )
                )
            if not attachment.url:
                errors.append(
                    ErrorDetail(
                        code=ErrorCode.INVALID_ATTACHMENT,
                        message="Attachment url is required.",
                        component="input_policy",
                    )
                )

        return errors

    def _infer_mime_from_url(self, url: str | None) -> str:
        if not url:
            return ""
        mime, _ = mimetypes.guess_type(url)
        return (mime or "").lower()


attachment_policy = AttachmentPolicy(
    max_message_length=settings.max_message_length,
    max_attachments=settings.max_attachments,
    max_attachment_bytes=settings.max_attachment_bytes,
    allowed_mime_types=settings.allowed_attachment_mime_types,
)
