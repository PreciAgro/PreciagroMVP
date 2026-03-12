"""
POST /analyze -- core intelligence endpoint.
Validates input -> assembles context -> calls Claude -> saves interaction -> returns structured response.
"""
import json
import logging
import os

import psycopg2
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.core import agroai, context
from backend.models.schemas import AnalyzeRequest, AnalyzeResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analyze"])


def _save_interaction(req: AnalyzeRequest, result: dict) -> None:
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO interactions
              (farmer_id, message_in, message_out, image_url, insight, action, confidence, urgency)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                req.farmer_id,
                req.message,
                json.dumps(result),
                req.image_url,
                result.get("insight"),
                result.get("action"),
                result.get("confidence"),
                result.get("urgency"),
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error("Failed to save interaction for farmer %s: %s", req.farmer_id, e)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(req: AnalyzeRequest):
    try:
        context_payload = await context.assemble_context(req.farmer_id)
    except Exception as e:
        logger.error("Context assembly failed for farmer %s: %s", req.farmer_id, e)
        context_payload = f"=== FARMER CONTEXT ===
farmer_id: {req.farmer_id}
(Context unavailable)
=== END CONTEXT ==="

    try:
        result = await agroai.analyze(
            image_url=req.image_url,
            context_payload=context_payload,
            message=req.message,
            farmer_id=req.farmer_id,
        )
    except Exception as e:
        logger.error("AgroAI analyze failed for farmer %s: %s", req.farmer_id, e)
        result = agroai.FALLBACK_RESPONSE

    _save_interaction(req, result)
    return AnalyzeResponse(**result)
