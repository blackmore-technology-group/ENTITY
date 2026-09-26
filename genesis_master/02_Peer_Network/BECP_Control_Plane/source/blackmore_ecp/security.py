from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from secrets import token_urlsafe
from typing import Any


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class SecurityError(PermissionError):
    pass


class SignedTokenService:
    def __init__(self, secret: str, issuer: str = "becp") -> None:
        if len(secret.encode("utf-8")) < 32:
            raise ValueError("BECP signing secret must be at least 32 bytes")
        self.key = secret.encode("utf-8")
        self.issuer = issuer
    def issue(self, claims: dict[str, Any], ttl_seconds: int, audience: str) -> str:
        now = int(time.time())
        payload = {
            "iss": self.issuer,
            "aud": audience,
            "iat": now,
            "exp": now + int(ttl_seconds),
            "jti": token_urlsafe(18),
            **claims,
        }
        body = _b64(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
        signature = _b64(hmac.new(self.key, body.encode(), hashlib.sha256).digest())
        return f"{body}.{signature}"

    def verify(self, token: str, audience: str) -> dict[str, Any]:
        try:
            body, signature = token.split(".", 1)
        except ValueError as exc:
            raise SecurityError("malformed token") from exc
        expected = _b64(hmac.new(self.key, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise SecurityError("invalid token signature")
        try:
            claims = json.loads(_unb64(body))
        except Exception as exc:
            raise SecurityError("invalid token payload") from exc
        now = int(time.time())
        if claims.get("iss") != self.issuer or claims.get("aud") != audience:
            raise SecurityError("token issuer or audience mismatch")
        if int(claims.get("exp", 0)) <= now:
            raise SecurityError("token expired")
        return claims


@dataclass
class ApprovalService:
    signer: SignedTokenService
    consumed: set[str]

    @classmethod
    def create(cls, signer: SignedTokenService) -> "ApprovalService":
        return cls(signer=signer, consumed=set())

    def issue(self, subject: str, capability: str, target: str, ttl_seconds: int = 300) -> str:
        return self.signer.issue(
            {"sub": subject, "capability": capability, "target": target},
            ttl_seconds=ttl_seconds,
            audience="becp-approval",
        )

    def consume(self, token: str, subject: str, capability: str, target: str) -> dict[str, Any]:
        claims = self.signer.verify(token, "becp-approval")
        if claims.get("sub") != subject:
            raise SecurityError("approval subject mismatch")
        if claims.get("capability") != capability or claims.get("target") != target:
            raise SecurityError("approval scope mismatch")
        jti = str(claims.get("jti", ""))
        if not jti or jti in self.consumed:
            raise SecurityError("approval already consumed")
        self.consumed.add(jti)
        return claims


def signing_secret_from_env(name: str = "BECP_SIGNING_KEY") -> str:
    secret = os.getenv(name, "")
    if not secret:
        raise RuntimeError(f"required secret is not configured: {name}")
    return secret
