import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invitation
from app.db.session import AsyncSessionLocal
from app.tasks.celery_app import celery_app

logger = logging.getLogger("survey_tasks")


async def _send_reminders_for_session(session: AsyncSession, survey_id: int) -> int:
    result = await session.execute(
        select(Invitation).where(
            Invitation.survey_id == survey_id,
            Invitation.used_at.is_(None),
            Invitation.email.is_not(None),
        )
    )
    pending = list(result.scalars().all())
    for invitation in pending:
        logger.info(
            "survey reminder sent: survey_id=%s invitation_id=%s email=%s",
            survey_id,
            invitation.id,
            invitation.email,
        )
        invitation.reminded_count = (invitation.reminded_count or 0) + 1
    await session.flush()
    return len(pending)


async def _send_reminders_async(survey_id: int) -> int:
    async with AsyncSessionLocal() as session:
        sent = await _send_reminders_for_session(session, survey_id)
        await session.commit()
        return sent


@celery_app.task(name="survey.send_reminders")
def send_survey_reminders(survey_id: int) -> int:
    return asyncio.run(_send_reminders_async(survey_id))
