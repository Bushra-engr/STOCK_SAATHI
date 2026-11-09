import logging
import ssl
from urllib.parse import urlparse

import certifi
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from database.config import settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

base_url = (settings.NEON_AUTH_BASE_URL or "").strip().rstrip("/")
_parsed = urlparse(base_url) if base_url else None

ALLOWED_ISSUERS: set[str] = set()
if base_url:
    ALLOWED_ISSUERS.update({base_url, f"{base_url}/"})
if _parsed and _parsed.netloc:
    origin = f"{_parsed.scheme}://{_parsed.netloc}"
    ALLOWED_ISSUERS.update({origin, f"{origin}/"})
explicit_issuer = settings.NEON_AUTH_ISSUER
if explicit_issuer and explicit_issuer.strip():
    custom_issuer = explicit_issuer.strip().rstrip("/")
    ALLOWED_ISSUERS.update({custom_issuer, f"{custom_issuer}/"})
ALLOWED_ISSUERS_LIST = sorted(ALLOWED_ISSUERS)

JWKS_URL = (
    (settings.NEON_AUTH_JWKS_URL or "").strip()
    or (f"{base_url}/.well-known/jwks.json" if base_url else "")
)

try:
    ssl_context = ssl.create_default_context(cafile=certifi.where())
except Exception:
    ssl_context = None

jwks_client = PyJWKClient(
    JWKS_URL,
    cache_jwk_set=True,
    lifespan=3600,
    timeout=5,
    ssl_context=ssl_context,
) if JWKS_URL else None

def verify_access_token(token: str) -> str:
    if not jwks_client:
        logger.error("Neon JWKS client is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service configuration is missing",
        )

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        unverified_header = jwt.get_unverified_header(token)
        algorithm = unverified_header.get("alg") or signing_key.algorithm_name
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            issuer=ALLOWED_ISSUERS_LIST or None,
            audience=settings.NEON_AUTH_AUDIENCE,
            options={
                "require": ["exp", "iss", "sub"],
                "verify_aud": bool(settings.NEON_AUTH_AUDIENCE),
            },
        )
        user_id = payload.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user identity",
            )
        return user_id

    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired; renew the Neon Auth token and retry",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidIssuerError as exc:
        logger.warning("Neon Auth token issuer mismatch; allowed issuers: %s", ALLOWED_ISSUERS_LIST)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token issuer does not match this Neon Auth branch",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token signature does not match the configured Neon JWKS",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidAlgorithmError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token algorithm does not match its Neon JWKS key",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.MissingRequiredClaimError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication token is missing required claim: {exc.claim}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.PyJWKClientConnectionError as exc:
        logger.warning("Unable to fetch Neon JWKS from %s: %s", JWKS_URL, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neon Auth signing keys are temporarily unreachable. Check that the backend can access the configured JWKS URL.",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication token rejected: {type(exc).__name__}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error during token verification: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify authentication at this time",
        ) from exc

def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_access_token(credentials.credentials)
