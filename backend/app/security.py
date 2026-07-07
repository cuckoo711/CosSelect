import secrets
import string

from itsdangerous import BadSignature, URLSafeSerializer

from .config import settings

_INVITE_ALPHABET = string.ascii_uppercase + string.digits
_serializer = URLSafeSerializer(settings.secret_key, salt="participant-token")


def gen_invite_code(length: int = 8) -> str:
    """8-char uppercase letters + digits invite code."""
    return "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(length))


def gen_manage_key() -> str:
    """Secret key that authorizes a leader to manage a space."""
    return secrets.token_urlsafe(24)


def make_participant_token(space_id: int, participant_id: int) -> str:
    return _serializer.dumps({"s": space_id, "p": participant_id})


def parse_participant_token(token: str) -> dict | None:
    try:
        data = _serializer.loads(token)
    except BadSignature:
        return None
    if not isinstance(data, dict) or "s" not in data or "p" not in data:
        return None
    return {"space_id": data["s"], "participant_id": data["p"]}
