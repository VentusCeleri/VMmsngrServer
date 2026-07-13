from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.pair import Pair
from app.models.user import User
from app.schemas.pair import JoinPairRequest, PairRead
from app.services.pairs import generate_invite_code

router = APIRouter(prefix="/api/v1/pairs", tags=["pairs"])


def find_user_pair(db: Session, user: User) -> Pair | None:
    return db.scalar(select(Pair).where(or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id)).limit(1))


@router.post("", response_model=PairRead, status_code=status.HTTP_201_CREATED)
def create_pair(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Pair:
    existing = find_user_pair(db, current_user)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has a pair")

    pair = Pair(user_a_id=current_user.id, invite_code=generate_invite_code(db))
    db.add(pair)
    db.commit()
    db.refresh(pair)
    return pair


@router.post("/join", response_model=PairRead)
def join_pair(
    payload: JoinPairRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Pair:
    existing = find_user_pair(db, current_user)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has a pair")

    pair = db.scalar(select(Pair).where(Pair.invite_code == payload.invite_code.upper()))
    if pair is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite code not found")
    if pair.user_a_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot join own pair")
    if pair.user_b_id is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pair is already full")

    pair.user_b_id = current_user.id
    db.add(pair)
    db.commit()
    db.refresh(pair)
    return pair


@router.get("/me", response_model=PairRead)
def get_my_pair(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Pair:
    pair = find_user_pair(db, current_user)
    if pair is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pair not found")
    return pair
