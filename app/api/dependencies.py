from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.pair import Pair
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    user = db.get(User, UUID(user_id)) if user_id else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_current_pair(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Pair:
    pair = db.scalar(
        select(Pair).where(or_(Pair.user_a_id == current_user.id, Pair.user_b_id == current_user.id)).limit(1)
    )
    if pair is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pair not found")
    return pair


def ensure_pair_member(pair: Pair, user_id: UUID) -> None:
    if pair.user_a_id != user_id and pair.user_b_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Pair access denied")


def ensure_pair_user(pair: Pair, user_id: UUID | None) -> None:
    if user_id is None:
        return
    if pair.user_a_id != user_id and pair.user_b_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not a pair member")
