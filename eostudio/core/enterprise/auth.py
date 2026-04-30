from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto


class AuthProvider(Enum):
    LOCAL = auto()
    OAUTH2 = auto()
    SAML = auto()
    OIDC = auto()
    LDAP = auto()


class Permission(Enum):
    READ = auto()
    WRITE = auto()
    ADMIN = auto()
    OWNER = auto()


@dataclass
class AuthConfig:
    provider: AuthProvider = AuthProvider.LOCAL
    client_id: str = ""
    client_secret: str = ""
    auth_url: str = ""
    token_url: str = ""
    redirect_uri: str = ""
    ldap_server: str = ""
    ldap_base_dn: str = ""


@dataclass
class UserSession:
    user_id: str
    username: str
    email: str
    roles: list[str] = field(default_factory=list)
    token: str = ""
    expires_at: str = ""
    permissions: list[Permission] = field(default_factory=list)


@dataclass
class AuditEntry:
    timestamp: str
    user_id: str
    action: str
    resource: str
    details: str = ""


class AuthManager:
    def __init__(self, config: AuthConfig | None = None) -> None:
        self._config = config or AuthConfig()
        self._sessions: dict[str, UserSession] = {}
        self._users: dict[str, dict] = {}
        self._audit_log: list[AuditEntry] = []

    def login(self, username: str, password: str) -> UserSession:
        user = self._users.get(username)
        if user is None:
            raise ValueError("Invalid username or password")
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        if user["password_hash"] != pw_hash:
            raise ValueError("Invalid username or password")
        token = secrets.token_urlsafe(32)
        session = UserSession(
            user_id=user["user_id"],
            username=username,
            email=user["email"],
            roles=user.get("roles", []),
            token=token,
            expires_at="",
            permissions=user.get("permissions", [Permission.READ]),
        )
        self._sessions[token] = session
        self.log_audit(AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=user["user_id"],
            action="login",
            resource="auth",
        ))
        return session

    def login_oauth(self, code: str) -> UserSession:
        token = secrets.token_urlsafe(32)
        session = UserSession(
            user_id=str(uuid.uuid4()),
            username=f"oauth-{code[:8]}",
            email="",
            roles=["user"],
            token=token,
            expires_at="",
            permissions=[Permission.READ, Permission.WRITE],
        )
        self._sessions[token] = session
        return session

    def logout(self, session: UserSession) -> None:
        self._sessions.pop(session.token, None)
        self.log_audit(AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=session.user_id,
            action="logout",
            resource="auth",
        ))

    def validate_session(self, token: str) -> UserSession | None:
        return self._sessions.get(token)

    def has_permission(self, session: UserSession, permission: Permission) -> bool:
        return permission in session.permissions

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: list[str] | None = None,
    ) -> dict:
        user_id = str(uuid.uuid4())
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        user = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "password_hash": pw_hash,
            "roles": roles or ["user"],
            "permissions": [Permission.READ, Permission.WRITE],
        }
        self._users[username] = user
        self.log_audit(AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=user_id,
            action="create_user",
            resource=f"user:{username}",
        ))
        return {"user_id": user_id, "username": username, "email": email}

    def get_audit_log(self, user_id: str | None = None) -> list[AuditEntry]:
        if user_id:
            return [e for e in self._audit_log if e.user_id == user_id]
        return list(self._audit_log)

    def log_audit(self, entry: AuditEntry) -> None:
        self._audit_log.append(entry)