# ruff: noqa: B008
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from jose import jwt

from app.api.deps import require_role
from app.core.config import settings
from app.core.limiter import limiter
from app.db.models import User, UserRole

router = APIRouter()


@router.post("/invitations", status_code=201)
@limiter.limit("30/minute")
async def create_invitation(
    request: Request,
    admin: User = Depends(require_role(UserRole.ADMIN)),  # noqa: B008
):
    now = datetime.now(UTC)
    exp = now + timedelta(days=7)
    payload = {
        "intended_role": "researcher",
        "issued_by": admin.id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return {"token": token, "expires_at": exp.isoformat()}
