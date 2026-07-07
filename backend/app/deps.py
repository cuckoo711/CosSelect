from datetime import datetime

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from .database import get_db
from .models import Participant, Space
from .response import ApiError
from .security import parse_participant_token


def get_space(space_id: int, db: Session = Depends(get_db)) -> Space:
    space = db.get(Space, space_id)
    if not space:
        raise ApiError("空间不存在", code=404, status_code=404)
    return space


def require_leader(
    space_id: int,
    x_manage_key: str | None = Header(default=None, alias="X-Manage-Key"),
    db: Session = Depends(get_db),
) -> Space:
    space = db.get(Space, space_id)
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
    return participant


class Actor:
    """Represents whoever is acting: leader or participant."""

    def __init__(self, space_id: int, is_leader: bool, participant: Participant | None):
        self.space_id = space_id
        self.is_leader = is_leader
        self.participant = participant

    @property
    def participant_id(self) -> int | None:
        return self.participant.id if self.participant else None

    @property
    def name(self) -> str:
        return "团长" if self.is_leader else (self.participant.nickname if self.participant else "")


def get_actor(
    space_id: int,
    x_manage_key: str | None = Header(default=None, alias="X-Manage-Key"),
    x_participant_token: str | None = Header(default=None, alias="X-Participant-Token"),
    db: Session = Depends(get_db),
) -> Actor:
    """Resolve the current actor for a space: leader (manage key) or participant (token)."""
    space = db.get(Space, space_id)
    if not space:
        raise ApiError("空间不存在", code=404, status_code=404)

    if x_manage_key and x_manage_key == space.manage_key:
        return Actor(space_id=space_id, is_leader=True, participant=None)

    if x_participant_token:
        payload = parse_participant_token(x_participant_token)
        if payload and payload["space_id"] == space_id:
            participant = db.get(Participant, payload["participant_id"])
            if participant and participant.space_id == space_id:
                return Actor(space_id=space_id, is_leader=False, participant=participant)

    raise ApiError("未授权访问", code=401, status_code=401)


def ensure_space_active(space: Space):
    if space.expire_time < datetime.utcnow():
        raise ApiError("口令已过期", code=410, status_code=410)
