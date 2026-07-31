import jwt
from followup_agent.config import Settings

NAMEID = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier"


class AuthError(Exception):
    pass


def user_id_from_token(token: str, settings: Settings) -> int:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_signing_key,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except jwt.PyJWTError as e:
        raise AuthError(str(e)) from e
    sub = payload.get(NAMEID)
    if sub is None:
        raise AuthError("missing nameidentifier claim")
    try:
        return int(sub)
    except ValueError as e:
        raise AuthError("nameidentifier claim is not an integer") from e
