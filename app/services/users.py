import re

USERNAME_PATTERN = re.compile(r"^[a-z0-9_.]{3,30}$")


def normalize_username(username: str) -> str:
    return username.strip().lower()


def validate_username(username: str) -> None:
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("username must be 3-30 chars and contain only latin letters, digits, underscore or dot")


def temporary_username(user_id: object, email: str) -> str:
    prefix = normalize_username(email.split("@", 1)[0])
    prefix = re.sub(r"[^a-z0-9_.]", ".", prefix).strip("._") or "user"
    prefix = prefix[:16]
    suffix = str(user_id).replace("-", "")[:10]
    return f"{prefix}.{suffix}"[:30]
