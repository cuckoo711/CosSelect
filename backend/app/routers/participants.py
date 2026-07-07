from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import ensure_space_active, get_space
from ..models import Participant, Space
from ..response import ok
from ..schemas import ParticipantJoin, ParticipantResp
from ..security import make_participant_token

router = APIRouter(prefix="/api/spaces/{space_id}/participants", tags=["participants"])


@router.post("")
def join_space(
    space_id: int,
    payload: ParticipantJoin,
    space: Space = Depends(get_space),
    db: Session = Depends(get_db),
):
    ensure_space_active(space)
    nickname = payload.nickname

    existing = (
        db.query(Participant)
        .filter(Participant.space_id == space_id, Participant.nickname == nickname)
        .first()
    )
    if existing:
        # Same nickname -> restore identity.
        token = make_participant_token(space_id, existing.id)
        return ok(
            ParticipantResp(
                participant_id=existing.id,
                nickname=existing.nickname,
                token=token,
                is_new=False,
            ).model_dump()
        )

    participant = Participant(space_id=space_id, nickname=nickname)
    db.add(participant)
    db.commit()
    db.refresh(participant)
    token = make_participant_token(space_id, participant.id)
    return ok(
        ParticipantResp(
            participant_id=participant.id,
            nickname=participant.nickname,
            token=token,
            is_new=True,
        ).model_dump()
    )


@router.get("/{nickname}")
def get_participant(
    space_id: int,
    nickname: str,
    space: Space = Depends(get_space),
    db: Session = Depends(get_db),
):
    participant = (
        db.query(Participant)
        .filter(Participant.space_id == space_id, Participant.nickname == nickname)
        .first()
    )
    if not participant:
        return ok({"exists": False})
    token = make_participant_token(space_id, participant.id)
    return ok(
        {
            "exists": True,
            "participant_id": participant.id,
            "nickname": participant.nickname,
            "token": token,
        }
    )
