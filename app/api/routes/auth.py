from datetime import datetime, timezone
from uuid import UUID

import logging

import jwt
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.errors import APIError
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.db.session import get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserRead

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
logger = logging.getLogger("vmmsngr.auth")


def issue_tokens(db: Session, user: User) -> TokenPair:
    access_token = create_access_token(user.id)
    refresh_token, token_id, expires_at = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_id=token_id,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


auth_rate_limit = Depends(rate_limit("auth", lambda: settings.rate_limit_auth_max_requests))


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED, dependencies=[auth_rate_limit])
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing is not None:
        raise APIError(status.HTTP_409_CONFLICT, "email_already_exists", "Email already registered")

    username_owner = db.scalar(select(User).where(User.username == payload.username))
    if username_owner is not None:
        raise APIError(status.HTTP_409_CONFLICT, "username_already_exists", "Username is already in use")

    user = User(
        email=payload.email.lower(),
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    tokens = issue_tokens(db, user)
    logger.info("User created", extra={"user_id": str(user.id)})
    return AuthResponse(**tokens.model_dump(), user=UserRead.model_validate(user))


@router.post("/login", response_model=AuthResponse, dependencies=[auth_rate_limit])
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        logger.info("Auth failure", extra={"client": request.client.host if request.client else "unknown"})
        raise APIError(status.HTTP_401_UNAUTHORIZED, "invalid_credentials", "Invalid email or password")

    tokens = issue_tokens(db, user)
    logger.info("User logged in", extra={"user_id": str(user.id), "client": request.client.host if request.client else "unknown"})
    return AuthResponse(**tokens.model_dump(), user=UserRead.model_validate(user))


@router.post("/refresh", response_model=TokenPair, dependencies=[auth_rate_limit])
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    try:
        decoded = decode_token(payload.refresh_token)
    except jwt.PyJWTError as exc:
        logger.error("Refresh JWT decode failed")
        raise APIError(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Invalid refresh token") from exc

    if decoded.get("type") != "refresh" or not decoded.get("jti") or not decoded.get("sub"):
        raise APIError(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Invalid refresh token")

    token_row = db.scalar(select(RefreshToken).where(RefreshToken.token_id == decoded["jti"]))
    now = datetime.now(timezone.utc)
    if token_row is None or token_row.revoked_at is not None or token_row.expires_at <= now:
        raise APIError(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Refresh token is not active")

    user = db.get(User, UUID(decoded["sub"]))
    if user is None:
        raise APIError(status.HTTP_401_UNAUTHORIZED, "unauthorized", "User not found")

    token_row.revoked_at = now
    db.add(token_row)
    tokens = issue_tokens(db, user)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if payload.refresh_token is None:
        db.query(RefreshToken).filter(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": datetime.now(timezone.utc)})
        db.commit()
        return

    try:
        decoded = decode_token(payload.refresh_token)
    except jwt.PyJWTError:
        logger.error("Logout JWT decode failed")
        return

    token_row = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_id == decoded.get("jti"),
            RefreshToken.user_id == current_user.id,
        )
    )
    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(timezone.utc)
        db.add(token_row)
        db.commit()


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
