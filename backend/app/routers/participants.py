from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import ensure_space_active, get_space
from ..models import Participant, Space
from ..response import ok
from ..schemas import ParticipantJoin, ParticipantResp
from ..security import make_participant_token
from ..ws import manager

router = APIRouter(prefix="/api/spaces/{space_id}/participants", tags=["participants"])


def _resp(participant: Participant, sid: int, is_new: bool) -> dict:
    token = make_participant_token(sid, participant.id)
    return ParticipantResp(
        participant_id=participant.id,
        nickname=participant.nickname,
        token=token,
        is_new=is_new,
        status=participant.status,
    ).model_dump()


@router.post("")
def join_space(
    space_id: str,
    payload: ParticipantJoin,
    space: Space = Depends(get_space),
    db: Session = Depends(get_db),
):
    ensure_space_active(space)
    sid = space.id
    nickname = payload.nickname

    existing = (
        db.query(Participant)
        .filter(Participant.space_id == sid, Participant.nickname == nickname)
        .first()
    )
    if existing:
        # Rejected participants may re-apply -> reset to pending (if approval on).
        if existing.status == "rejected":
            existing.status = "pending" if space.require_approval else "approved"
            db.commit()
            db.refresh(existing)
            if existing.status == "pending":
                _notify_new_request(space.public_id, existing)
        return ok(_resp(existing, sid, is_new=False))

    status = "pending" if space.require_approval else "approved"
    participant = Participant(space_id=sid, nickname=nickname, status=status)
    db.add(participant)
    db.commit()
    db.refresh(participant)
    if status == "pending":
        _notify_new_request(space.public_id, participant)
    return ok(_resp(participant, sid, is_new=True))


@router.get("/{nickname}")
def get_participant(
    space_id: str,
    nickname: str,
    space: Space = Depends(get_space),
    db: Session = Depends(get_db),
):
    participant = (
        db.query(Participant)
        .filter(Participant.space_id == space.id, Participant.nickname == nickname)
        .first()
    )
    if not participant:
        return ok({"exists": False})
    return ok(
        {
            "exists": True,
            **_resp(participant, space.id, is_new=False),
        }
    )


@router.get("/me/status")
def my_status(
    space_id: str,
    space: Space = Depends(get_space),
    nickname: str = "",
    db: Session = Depends(get_db),
):
    """Poll a participant's approval status by nickname (fallback for WS)."""
    participant = (
        db.query(Participant)
        .filter(Participant.space_id == space.id, Participant.nickname == nickname)
        .first()
    )
    if not participant:
        return ok({"status": "none"})
    return ok({"status": participant.status, "participant_id": participant.id})


def _notify_new_request(space_pid: str, participant: Participant):
    manager.broadcast_threadsafe(
        space_pid,
        {
            "type": "join_request",
            "participant_id": participant.id,
            "nickname": participant.nickname,
        },
    )
