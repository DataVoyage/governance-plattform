"""Authentifizierung ueber die zentrale Unternehmensidentitaet (Architektur 10.1).

Kein separates Passwort, kein lokaler Account. Der Entwicklungsmodus
(``GP_AUTH_DEV_MODE``) ersetzt lediglich den Aussteller des Tokens, nicht die
Pruefkette: auch dort wird ein signiertes JWT erwartet und validiert.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from jose import jwt
from jose.exceptions import JWTError

from app.config import Settings

_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}
JWKS_TTL_SECONDS = 300


class AuthError(Exception):
    """Token fehlt, ist abgelaufen oder nicht verifizierbar."""


def _fetch_jwks(url: str) -> dict[str, Any]:
    cached = _jwks_cache.get(url)
    if cached and cached[0] > time.time():
        return cached[1]
    response = httpx.get(url, timeout=10.0)
    response.raise_for_status()
    jwks = response.json()
    _jwks_cache[url] = (time.time() + JWKS_TTL_SECONDS, jwks)
    return jwks


def clear_jwks_cache() -> None:
    _jwks_cache.clear()


def issue_dev_token(settings: Settings, subject: str, email: str, name: str) -> str:
    """Nur im Entwicklungsmodus: stellt ein lokal signiertes Token aus."""
    if not settings.auth_dev_mode:
        raise AuthError("Entwicklungs-Token nur bei GP_AUTH_DEV_MODE=true")
    claims = {
        "sub": subject,
        "email": email,
        "name": name,
        "iss": "governance-plattform-dev",
        "aud": settings.oidc_audience or "governance-plattform",
        "exp": int(time.time()) + 8 * 3600,
        "iat": int(time.time()),
    }
    return jwt.encode(claims, settings.auth_dev_secret, algorithm="HS256")


def verify_token(token: str, settings: Settings) -> dict[str, Any]:
    """Verifiziert ein Zugangstoken und liefert seine Claims."""
    audience = settings.oidc_audience or "governance-plattform"
    try:
        if settings.auth_dev_mode:
            return jwt.decode(
                token,
                settings.auth_dev_secret,
                algorithms=["HS256"],
                audience=audience,
                issuer="governance-plattform-dev",
            )
        if not settings.oidc_jwks_url:
            raise AuthError("OIDC ist nicht konfiguriert")
        jwks = _fetch_jwks(settings.oidc_jwks_url)
        return jwt.decode(
            token,
            jwks,
            algorithms=["RS256", "ES256"],
            audience=audience,
            issuer=settings.oidc_issuer or None,
        )
    except JWTError as exc:
        raise AuthError(str(exc)) from exc


def claims_to_identity(claims: dict[str, Any]) -> tuple[str, str, str]:
    """Extrahiert ``(subject, email, name)`` aus den Token-Claims."""
    subject = claims.get("sub")
    if not subject:
        raise AuthError("Token ohne 'sub'-Claim")
    email = claims.get("email") or f"{subject}@unbekannt.invalid"
    name = claims.get("name") or email
    return str(subject), str(email), str(name)
