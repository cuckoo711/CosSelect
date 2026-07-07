from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import require_leader
from ..models import Space
from ..response import ok
from ..schemas import InviteCodeResp, SpaceCreateResp, VerifyResp
from ..security import gen_invite_code, gen_manage_key, gen_public_id

router = APIRouter(prefix="/api/spaces", tags=["spaces"])


def _new_expire() -> datetime:
    return datetime.utcnow() + timedelta(hours=settings.invite_code_ttl_hours)


def _unique_public_id(db: Session) -> str:
    for _ in range(10):
        pid = gen_public_id()
        if not db.query(Space).filter(Space.public_id == pid).first():
            return pid
    return gen_public_id(12)


@router.post("")
def create_space(db: Session = Depends(get_db)):
    space = Space(
        public_id=_unique_public_id(db),
        invite_code=gen_invite_code(),
        manage_key=gen_manage_key(),
        expire_time=_new_expire(),
    )
    db.add(space)
    db.commit()
    db.refresh(space)
    return ok(
        SpaceCreateResp(
            space_id=space.public_id,
            invite_code=space.invite_code,
            manage_key=space.manage_key,
            expire_time=space.expire_time,
        ).model_dump()
    )


@router.post("/{space_id}/regenerate-code")
def regenerate_code(space_id: str, space: Space = Depends(require_leader), db: Session = Depends(get_db)):
    space.invite_code = gen_invite_code()
    space.expire_time = _new_expire()
    db.commit()
    db.refresh(space)
    return ok(
        InviteCodeResp(
            space_id=space.public_id,
            invite_code=space.invite_code,
            expire_time=space.expire_time,
        ).model_dump()
    )


@router.get("/{space_id}/verify")
def verify_code(space_id: str, code: str, db: Session = Depends(get_db)):
    space = db.query(Space).filter(Space.public_id == space_id).first()
    valid = bool(
        space
        and space.invite_code == code.upper().strip()
        and space.expire_time >= datetime.utcnow()
    )
    return ok(VerifyResp(valid=valid, space_id=space_id).model_dump())


@router.get("/{space_id}/info")
def space_info(space_id: str, space: Space = Depends(require_leader)):
    """Leader-only: current invite code and expiry."""
    return ok(
        {
            "space_id": space.public_id,
            "invite_code": space.invite_code,
            "expire_time": space.expire_time.isoformat(),
            "expired": space.expire_time < datetime.utcnow(),
            "require_approval": space.require_approval,
            "last_access_at": space.last_access_at.isoformat() if space.last_access_at else None,
            "inactive_notice_days": settings.inactive_notice_days,
            "inactive_destroy_days": settings.inactive_destroy_days,
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
    return ok({"valid": True, "space_id": space.public_id})
