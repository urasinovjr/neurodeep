import asyncio
import logging
import time
import uuid
from decimal import Decimal

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.redis import make_redis_client
from app.db.models import (
    Question,
    QuestionScale,
    ScaleScore,
    Survey,
    SurveySession,
)
from app.db.session import AsyncSessionLocal
from app.tasks.celery_app import celery_app

logger = logging.getLogger("process_answer")

ANSWER_KEY_PREFIX = "answer"
PROCESSED_KEY_PREFIX = "processed"
PROCESSED_TTL_SECONDS = 86400
NLP_TIMEOUT_SECONDS = 10.0


def _clamp_value(raw: float) -> Decimal:
    bounded = max(0.0, min(100.0, raw))
    return Decimal(str(round(bounded, 2)))


def _clamp_confidence(raw: float) -> Decimal:
    bounded = max(0.0, min(1.0, raw))
    return Decimal(str(round(bounded, 2)))


async def _process_answer_async(
    session_id_str: str, question_id: int
) -> dict[str, str | int]:
    started = time.monotonic()
    redis = make_redis_client()
    try:
        processed_key = f"{PROCESSED_KEY_PREFIX}:{session_id_str}:{question_id}"
        if await redis.get(processed_key):
            logger.info(
                "process_answer skip already_processed: session_id=%s question_id=%s",
                session_id_str,
                question_id,
            )
            return {"status": "skipped"}

        answer_key = f"{ANSWER_KEY_PREFIX}:{session_id_str}:{question_id}"
        text = await redis.get(answer_key)
        if not text:
            logger.warning(
                "process_answer error no_text: session_id=%s question_id=%s",
                session_id_str,
                question_id,
            )
            return {"status": "error_no_text"}

        try:
            session_uuid = uuid.UUID(session_id_str)
        except ValueError:
            logger.warning(
                "process_answer error bad_uuid: session_id=%s", session_id_str
            )
            return {"status": "error_bad_session_id"}

        async with AsyncSessionLocal() as db:
            survey_session = await db.get(SurveySession, session_uuid)
            if survey_session is None:
                logger.warning(
                    "process_answer error session_not_found: session_id=%s",
                    session_id_str,
                )
                return {"status": "error_session_not_found"}

            question = await db.get(Question, question_id)
            if question is None:
                logger.warning(
                    "process_answer error question_not_found: question_id=%s",
                    question_id,
                )
                return {"status": "error_question_not_found"}

            survey = await db.get(Survey, survey_session.survey_id)
            if survey is None:
                logger.warning(
                    "process_answer error survey_not_found: session_id=%s",
                    session_id_str,
                )
                return {"status": "error_survey_not_found"}

            links_result = await db.execute(
                select(QuestionScale).where(
                    QuestionScale.question_id == question_id
                )
            )
            scale_ids = [link.scale_id for link in links_result.scalars()]
            if not scale_ids:
                logger.warning(
                    "process_answer error no_scales: question_id=%s", question_id
                )
                return {"status": "error_no_scales"}

            try:
                async with httpx.AsyncClient(timeout=NLP_TIMEOUT_SECONDS) as client:
                    response = await client.post(
                        f"{settings.NLP_SERVICE_URL}/predict",
                        json={
                            "text": text,
                            "scale_ids": scale_ids,
                            "methodology_id": survey.methodology_id,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
            except httpx.HTTPError as exc:
                logger.warning(
                    "process_answer NLP error: session_id=%s question_id=%s error=%s",
                    session_id_str,
                    question_id,
                    type(exc).__name__,
                )
                return {"status": "error_nlp"}

            scores_dict = payload.get("scores") or {}
            new_rows: list[ScaleScore] = []
            allowed = set(scale_ids)
            for scale_id_str, body in scores_dict.items():
                try:
                    scale_id = int(scale_id_str)
                except (TypeError, ValueError):
                    continue
                if scale_id not in allowed:
                    continue
                if not isinstance(body, dict):
                    continue
                value = float(body.get("value", 50.0))
                confidence = float(body.get("confidence", 0.0))
                new_rows.append(
                    ScaleScore(
                        session_id=session_uuid,
                        scale_id=scale_id,
                        value=_clamp_value(value),
                        confidence=_clamp_confidence(confidence),
                    )
                )

            if new_rows:
                db.add_all(new_rows)
            await db.commit()

        await redis.setex(processed_key, PROCESSED_TTL_SECONDS, "1")
        await redis.delete(answer_key)

        latency_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "process_answer done: session_id=%s question_id=%s scores_count=%s latency_ms=%s",
            session_id_str,
            question_id,
            len(new_rows),
            latency_ms,
        )
        return {"status": "ok", "scores_count": len(new_rows)}
    finally:
        await redis.aclose()


@celery_app.task(name="survey.process_answer")
def process_answer(session_id: str, question_id: int) -> dict[str, str | int]:
    return asyncio.run(_process_answer_async(session_id, question_id))
