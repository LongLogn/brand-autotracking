"""Xác minh Cognito access token; cấu hình tin cậy đến từ môi trường server."""
import os
from functools import lru_cache
from urllib.parse import urlsplit

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

bearer = HTTPBearer(auto_error=False)
REQUIRED_SCOPE = "brand-api/access"


@lru_cache(maxsize=1)
def configuration():
    issuer = os.getenv("COGNITO_ISSUER", "").rstrip("/")
    client_id = os.getenv("COGNITO_CLIENT_ID", "")
    url = urlsplit(issuer)
    if url.scheme != "https" or not url.hostname or not client_id or url.username or url.password or url.query or url.fragment:
        raise RuntimeError("Thiếu hoặc sai COGNITO_ISSUER / COGNITO_CLIENT_ID")
    return issuer, client_id, PyJWKClient(f"{issuer}/.well-known/jwks.json", timeout=5)


def current_subject(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Không xác thực", headers={"WWW-Authenticate": "Bearer"})
    try:
        issuer, client_id, jwks = configuration()
    except (RuntimeError, ValueError):
        raise HTTPException(status_code=503, detail="Dịch vụ xác thực chưa sẵn sàng") from None
    try:
        signing_key = jwks.get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(credentials.credentials, signing_key.key, algorithms=["RS256"], issuer=issuer,
                            options={"require": ["exp", "iss", "sub", "token_use", "client_id"], "verify_aud": False})
        if claims.get("token_use") != "access" or claims.get("client_id") != client_id or not isinstance(claims.get("sub"), str) or not claims["sub"].strip():
            raise jwt.InvalidTokenError("Sai thông tin token")
        scopes = claims.get("scope")
        if not isinstance(scopes, str) or REQUIRED_SCOPE not in scopes.split():
            raise HTTPException(status_code=403, detail="Token không có quyền truy cập API")
        return claims["sub"]
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(status_code=503, detail="Dịch vụ xác thực chưa sẵn sàng") from None
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Không xác thực", headers={"WWW-Authenticate": "Bearer"}) from None
