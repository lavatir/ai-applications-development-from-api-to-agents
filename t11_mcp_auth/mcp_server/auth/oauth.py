import asyncio
import os

import requests
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# ==================== CONFIGURATION ====================

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8089")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp-realm")
REQUIRED_ROLE = os.getenv("MCP_REQUIRED_ROLE", "mcp-tools-access")

ISSUER = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"

# ==================== JWKS CACHE ====================

# Public keys are fetched once from Keycloak and cached in memory.
# This avoids a round-trip to Keycloak on every MCP request.
# Cache is invalidated on server restart; for production you'd add TTL-based refresh.
_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    """Fetch and cache Keycloak public keys (JWKS)"""
    global _jwks_cache

    if _jwks_cache is None:
        print("🔑 Fetching JWKS from ...")
        response = await asyncio.to_thread(requests.get, JWKS_URL)
        response.raise_for_status()
        _jwks_cache = response.json()
        print("🔑 JWKS cached successfully")

    assert _jwks_cache is not None
    return _jwks_cache


# ==================== MIDDLEWARE ====================


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that:
      1. Extracts the Bearer token from the Authorization header
      2. Validates JWT signature using Keycloak public keys (JWKS)
      3. Verifies token issuer and expiry
      4. Checks that the user has the required realm role
    """

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization", "")

        # ── Step 1: Check header presence ──────────────────────────────
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or invalid Authorization header"},
            )

        token = auth_header.removeprefix("Bearer ")

        # ── Step 2: Validate JWT signature + claims ─────────────────────
        jwks = await _get_jwks()
        try:
            claims = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                issuer=ISSUER,
                options={"verify_aud": False},
            )
        except JWTError as e:
            return JSONResponse(
                status_code=401, content={"error": f"Invalid token: {e}"}
            )

        # ── Step 3: Check realm role ────────────────────────────────────
        # Keycloak embeds roles in: claims["realm_access"]["roles"]
        roles = claims.get("realm_access", {}).get("roles", [])
        if REQUIRED_ROLE not in roles:
            return JSONResponse(
                status_code=403,
                content={
                    "error": f"Missing required role '{REQUIRED_ROLE}'",
                    "roles": roles,
                },
            )

        print(
            f"✅ Authenticated user: {claims.get('preferred_username')} with roles: {roles}"
        )
        return await call_next(request)
