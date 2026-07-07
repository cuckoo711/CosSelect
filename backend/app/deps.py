from datetime import datetime, timedelta

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from .database import get_db
from .models import Participant, Space
from .response import ApiError
from .security import parse_participant_token

# only persist last_access_at at most once per this interval to avoid write churn
_ACCESS_TOUCH_INTERVAL = timedelta(minutes=30)


def touch_access(db: Session, space: Space):
    """Record that the space was accessed (used for inactivity auto-destroy)."""
    now = datetime.utcnow()
    if not space.last_access_at or (now - space.last_access_at) > _ACCESS_TOUCH_INTERVAL:
        space.last_access_at = now
        try:
            db.commit()
        except Exception:
            db.rollback()


def resolve_space(db: Session, public_id: str) -> Space | None:
    space = db.query(Space).filter(Space.public_id == public_id).first()
    if space:
        touch_access(db, space)
    return space


def get_space(space_id: str, db: Session = Depends(get_db)) -> Space:
    space = resolve_space(db, space_id)
    if not space:
        raise ApiError("空间不存在", code=404, status_code=404)
    return space


def require_leader(
    space_id: str,
    x_manage_key: str | None = Header(default=None, alias="X-Manage-Key"),
    db: Session = Depends(get_db),
) -> Space:
    space = resolve_space(db, space_id)
    if not space:
        raise ApiError("空间不存在", code=404, status_code=404)
    if not x_manage_key or x_manage_key != space.manage_key:
        raise ApiError("无权限：团长密钥无效", code=403, status_code=403)
    return space


def require_participant(
    x_participant_token: str | None = Header(default=None, alias="X-Participant-Token"),
    db: Session = Depends(get_db),
) -> Participant:
    if not x_participant_token:
        raise ApiError("未提供身份令牌", code=401, status_code=401)
    payload = parse_participant_token(x_participant_token)
    if not payload:
        raise ApiError("身份令牌无效", code=401, status_code=401)
    participant = db.get(Participant, payload["participant_id"])
    if not participant or participant.space_id != payload["space_id"]:
        raise ApiError("身份不存在", code=401, status_code=401)
    _ensure_approved(participant)
    return participant


def _ensure_approved(participant: Participant):
    if participant.status == "pending":
        raise ApiError("等待团长审批中", code=428, status_code=428)
    if participant.status == "rejected":
        raise ApiError("加入申请已被拒绝", code=403, status_code=403)


class Actor:
    """Represents whoever is acting: leader or participant."""

    def __init__(
        self,
        space_id: int,
        space_public_id: str,
        is_leader: bool,
        participant: Participant | None,
    ):
        self.space_id = space_id  # internal integer id (for DB queries)
        self.space_public_id = space_public_id  # exposed id (for URLs)
        self.is_leader = is_leader
        self.participant = participant

    @property
    def participant_id(self) -> int | None:
        return self.participant.id if self.participant else None

    @property
    def name(self) -> str:
        return "团长" if self.is_leader else (self.participant.nickname if self.participant else "")


def get_actor(
    space_id: str,
    x_manage_key: str | None = Header(default=None, alias="X-Manage-Key"),
    x_participant_token: str | None = Header(default=None, alias="X-Participant-Token"),
    db: Session = Depends(get_db),
) -> Actor:
    """Resolve the current actor for a space: leader (manage key) or participant (token)."""
    space = resolve_space(db, space_id)
    if not space:
        raise ApiError("空间不存在", code=404, status_code=404)

    if x_manage_key and x_manage_key == space.manage_key:
        return Actor(
            space_id=space.id, space_public_id=space.public_id, is_leader=True, participant=None
        )

    if x_participant_token:
        payload = parse_participant_token(x_participant_token)
        if payload and payload["space_id"] == space.id:
            participant = db.get(Participant, payload["participant_id"])
            if participant and participant.space_id == space.id:
                _ensure_approved(participant)
                return Actor(
                    space_id=space.id,
                    space_public_id=space.public_id,
                    is_leader=False,
                    participant=participant,
                )

    raise ApiError("未授权访问", code=401, status_code=401)


def ensure_space_active(space: Space):
    if space.expire_time < datetime.utcnow():
        raise ApiError("口令已过期", code=410, status_code=410)
