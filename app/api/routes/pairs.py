import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.errors import APIError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.message import Message
from app.models.pair import Pair
from app.models.task import Task
from app.models.user import User
from app.notifications.events import notify_pair_joined, pair_recipient_ids
from app.realtime.manager import realtime_manager
from app.schemas.pair import JoinPairRequest, PairRead
from app.schemas.realtime import make_realtime_event
from app.schemas.user import PartnerPresenceRead, PartnerProfileRead, UserRead
from app.services.pairs import generate_invite_code

router = APIRouter(prefix="/api/v1/pairs", tags=["pairs"])
logger = logging.getLogger("vmmsngr.pairs")


def find_user_pair(db: Session, user: User) -> Pair | None:
    return db.scalar(select(Pair).where(or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id)).limit(1))


@router.post("", response_model=PairRead, status_code=status.HTTP_201_CREATED)
def create_pair(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Pair:
    existing = find_user_pair(db, current_user)
    if existing is not None:
        raise APIError(status.HTTP_409_CONFLICT, "pair_already_exists", "User already has a pair")

    pair = Pair(user_a_id=current_user.id, invite_code=generate_invite_code(db))
    db.add(pair)
    db.commit()
    db.refresh(pair)
    logger.info("Pair created", extra={"pair_id": str(pair.id), "user_id": str(current_user.id)})
    return pair


@router.post(
    "/join",
    response_model=PairRead,
    dependencies=[Depends(rate_limit("pair_join", lambda: settings.rate_limit_pair_join_max_requests))],
)
async def join_pair(
    payload: JoinPairRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Pair:
    existing = find_user_pair(db, current_user)
    if existing is not None:
        raise APIError(status.HTTP_409_CONFLICT, "pair_already_exists", "User already has a pair")

    pair = db.scalar(select(Pair).where(Pair.invite_code == payload.invite_code.upper()))
    if pair is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "invalid_invite_code", "Invite code not found")
    if pair.user_a_id == current_user.id or pair.user_b_id == current_user.id:
        raise APIError(status.HTTP_409_CONFLICT, "cannot_join_own_pair", "Cannot join own pair")
    if pair.user_a_id is None:
        pair.user_a_id = current_user.id
    elif pair.user_b_id is None:
        pair.user_b_id = current_user.id
    else:
        raise APIError(status.HTTP_409_CONFLICT, "pair_full", "Pair is already full")

    db.add(pair)
    db.commit()
    db.refresh(pair)
    logger.info("Pair joined", extra={"pair_id": str(pair.id), "user_id": str(current_user.id)})
    await notify_pair_joined(db, current_user, pair_recipient_ids(pair, current_user.id), pair.id)
    return pair


@router.get("/me", response_model=PairRead)
def get_my_pair(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Pair:
    pair = find_user_pair(db, current_user)
    if pair is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "no_pair", "Pair not found")
    return pair


@router.post("/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_pair(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    pair = find_user_pair(db, current_user)
    if pair is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "no_pair", "Pair not found")

    pair_id = pair.id
    try:
        if pair.user_a_id == current_user.id:
            pair.user_a_id = None
        elif pair.user_b_id == current_user.id:
            pair.user_b_id = None
        else:
            raise APIError(status.HTTP_403_FORBIDDEN, "forbidden", "Pair access denied")

        pair_deleted = pair.user_a_id is None and pair.user_b_id is None
        pair_payload: dict | None = None
        if pair_deleted:
            db.execute(delete(Message).where(Message.pair_id == pair_id))
            db.execute(delete(Task).where(Task.pair_id == pair_id))
            db.delete(pair)
        else:
            db.add(pair)
            db.flush()
            pair_payload = PairRead.model_validate(pair).model_dump(mode="json")

        db.commit()
    except APIError:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Pair leave failed", extra={"pair_id": str(pair_id), "user_id": str(current_user.id)})
        raise APIError(status.HTTP_500_INTERNAL_SERVER_ERROR, "database_error", "Could not leave pair") from exc

    logger.info("Pair left", extra={"pair_id": str(pair_id), "user_id": str(current_user.id)})
    await realtime_manager.broadcast_pair(
        pair_id,
        make_realtime_event("user.left", pair_id, {"pair_id": str(pair_id), "user_id": str(current_user.id)}),
    )
    if pair_deleted:
        await realtime_manager.broadcast_pair(pair_id, make_realtime_event("pair.deleted", pair_id, {"pair_id": str(pair_id)}))
        await realtime_manager.close_pair(pair_id)
    else:
        await realtime_manager.broadcast_pair(
            pair_id,
            make_realtime_event("pair.updated", pair_id, pair_payload or {"pair_id": str(pair_id)}),
        )
        await realtime_manager.close_user(current_user.id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_pair(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    pair = find_user_pair(db, current_user)
    if pair is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "no_pair", "Pair not found")

    pair_id = pair.id
    try:
        db.execute(delete(Message).where(Message.pair_id == pair_id))
        db.execute(delete(Task).where(Task.pair_id == pair_id))
        db.delete(pair)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Pair delete failed", extra={"pair_id": str(pair_id), "user_id": str(current_user.id)})
        raise APIError(status.HTTP_500_INTERNAL_SERVER_ERROR, "database_error", "Could not delete pair") from exc

    logger.info("Pair deleted", extra={"pair_id": str(pair_id), "user_id": str(current_user.id)})
    await realtime_manager.broadcast_pair(pair_id, make_realtime_event("pair.deleted", pair_id, {"pair_id": str(pair_id)}))
    await realtime_manager.close_pair(pair_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me/partner", response_model=PartnerProfileRead)
def get_partner_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PartnerProfileRead:
    pair = find_user_pair(db, current_user)
    if pair is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "no_pair", "Pair not found")

    partner_id = pair.user_b_id if pair.user_a_id == current_user.id else pair.user_a_id
    if partner_id is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "partner_not_found", "Partner not found")

    partner = db.get(User, partner_id)
    if partner is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "partner_not_found", "Partner not found")

    return PartnerProfileRead(
        user=UserRead.model_validate(partner),
        presence=PartnerPresenceRead(
            user_id=partner.id,
            is_online=realtime_manager.is_user_online(partner.id),
            last_seen_at=partner.last_seen_at,
        ),
    )
