from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import require_leader
from ..models import Space
from ..response import ok
from ..schemas import InviteCodeResp, SpaceCreateResp, VerifyResp
from ..security import gen_invite_code, gen_manage_key

router = APIRouter(prefix="/api/spaces", tags=["spaces"])


def _new_expire() -> datetime:
    return datetime.utcnow() + timedelta(hours=settings.invite_code_ttl_hours)


@router.post("")
def create_space(db: Session = Depends(get_db)):
    space = Space(
        invite_code=gen_invite_code(),
        manage_key=gen_manage_key(),
        expire_time=_new_expire(),
    )
    db.add(space)
    db.commit()
    db.refresh(space)
    return ok(
        SpaceCreateResp(
            space_id=space.id,
            invite_code=space.invite_code,
            manage_key=space.manage_key,
            expire_time=space.expire_time,
        ).model_dump()
    )


@router.post("/{space_id}/regenerate-code")
def regenerate_code(space_id: int, space: Space = Depends(require_leader), db: Session = Depends(get_db)):
    space.invite_code = gen_invite_code()
    space.expire_time = _new_expire()
    db.commit()
    db.refresh(space)
    return ok(
        InviteCodeResp(
            space_id=space.id,
            invite_code=space.invite_code,
            expire_time=space.expire_time,
        ).model_dump()
    )


@router.get("/{space_id}/verify")
def verify_code(space_id: int, code: str, db: Session = Depends(get_db)):
    space = db.get(Space, space_id)
    valid = bool(
        space
        and space.invite_code == code.upper().strip()
        and space.expire_time >= datetime.utcnow()
    )
    return ok(VerifyResp(valid=valid, space_id=space_id).model_dump())


@router.get("/{space_id}/info")
def space_info(space_id: int, space: Space = Depends(require_leader)):
    """Leader-only: current invite code and expiry."""
    return ok(
        {
            "space_id": space.id,
            "invite_code": space.invite_code,
            "expire_time": space.expire_time.isoformat(),
            "expired": space.expire_time < datetime.utcnow(),
        }
    )


@router.post("/verify-code")
def verify_code_global(payload: dict, db: Session = Depends(get_db)):
    """Verify by invite code only (no space_id known): find matching active space."""
    code = str(payload.get("code", "")).upper().strip()
    space = (
        db.query(Space)
        .filter(Space.invite_code == code, Space.expire_time >= datetime.utcnow())
        .order_by(Space.created_at.desc())
        .first()
    )
    if not space:
        return ok({"valid": False, "space_id": None})
    return ok({"valid": True, "space_id": space.id})
