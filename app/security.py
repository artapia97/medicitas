"""Password hashing, JWT handling and internal-network restriction."""
from datetime import UTC, datetime, timedelta
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

ALGORITHM = "HS256"

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(admin_id: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(admin_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expiration_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_admin_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> int:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Token de autenticación ausente.")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.secret_key, algorithms=[ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("La sesión ha expirado. Inicie sesión nuevamente.")
    except jwt.InvalidTokenError:
        raise _unauthorized("Token inválido.")
    sub = payload.get("sub")
    try:
        return int(sub)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise _unauthorized("Token inválido.")


CurrentAdminId = Annotated[int, Depends(get_current_admin_id)]


_IPAddress = IPv4Address | IPv6Address
_IPNetwork = IPv4Network | IPv6Network


def _parse_networks(raw: list[str]) -> list[_IPNetwork]:
    return [ip_network(entry, strict=False) for entry in raw]


_ALLOWED_NETWORKS: list[_IPNetwork] = _parse_networks(settings.internal_networks_list)


def _is_internal(client_ip: str) -> bool:
    try:
        addr = ip_address(client_ip)
    except ValueError:
        return False
    # Unmap IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1) before comparing.
    if isinstance(addr, IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    for network in _ALLOWED_NETWORKS:
        if addr.version == network.version and addr in network:
            return True
    return False


def require_internal_network(request: Request) -> None:
    client = request.client
    host = client.host if client is not None else ""
    if not host or not _is_internal(host):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "La agenda pública solo está disponible desde la red "
                "interna del centro médico."
            ),
        )