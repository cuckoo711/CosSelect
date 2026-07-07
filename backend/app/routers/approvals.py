from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_leader
from ..models import Participant, Space
from ..response import ApiError, ok
from ..schemas import ApprovalItem
from ..ws import manager

router = APIRouter(prefix="/api/spaces/{space_id}", tags=["approvals"])


@router.get("/participants-list")
def list_participants(
    space_id: str,
    status: str = Query("pending", pattern="^(pending|approved|rejected|all)$"),
    space: Space = Depends(require_leader),
    db: Session = Depends(get_db),
):
    q = db.query(Participant).filter(Participant.space_id == space.id)
    if status != "all":
        q = q.filter(Participant.status == status)
    rows = q.order_by(Participant.join_time.desc()).all()
    return ok(
        [
            ApprovalItem(
                participant_id=p.id,
                nickname=p.nickname,
                status=p.status,
                join_time=p.join_time,
            ).model_dump()
            for p in rows
        ]
    )


@router.post("/participants/{participant_id}/approve")
def approve_participant(
    space_id: str,
    participant_id: int,
    space: Space = Depends(require_leader),
    db: Session = Depends(get_db),
):
    return _set_status(db, space, participant_id, "approved")


@router.post("/participants/{participant_id}/reject")
def reject_participant(
    space_id: str,
    participant_id: int,
    space: Space = Depends(require_leader),
    db: Session = Depends(get_db),
):
    return _set_status(db, space, participant_id, "rejected")


def _set_status(db: Session, space: Space, participant_id: int, status: str):
    participant = db.get(Participant, participant_id)
    if not participant or participant.space_id != space.id:
        raise ApiError("参与者不存在", code=404, status_code=404)
    participant.status = status
    db.commit()
    manager.broadcast_threadsafe(
        space.public_id,
        {
            "type": "approval_result",
            "participant_id": participant.id,
            "nickname": participant.nickname,
            "status": status,
        },
    )
    return ok({"participant_id": participant.id, "status": status})


@router.put("/settings/approval")
def set_approval_setting(
    space_id: str,
    payload: dict,
    space: Space = Depends(require_leader),
    db: Session = Depends(get_db),
):
    require = bool(payload.get("require_approval", True))
    space.require_approval = require
    db.commit()
    return ok({"require_approval": space.require_approval})
