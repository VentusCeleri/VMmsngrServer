import secrets
import string

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pair import Pair

INVITE_ALPHABET = string.ascii_uppercase + string.digits


def generate_invite_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(8))
        exists = db.scalar(select(Pair.id).where(Pair.invite_code == code))
        if exists is None:
            return code
