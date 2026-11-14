"""Segredos só no servidor; autorização e cotas independentes dos widgets."""
from dataclasses import dataclass, field
import hashlib
import hmac
import os
import time

MODEL = 'gpt-6-luna'
MODEL_VERSION = MODEL  # ID oficial; o fornecedor não publica snapshot separado para este modelo.
ALLOWED_MODELS = (MODEL, 'gpt-4.1-mini-2025-04-14')
MAX_SESSION_CALLS = 6
AUTH_SECONDS = 900


@dataclass(frozen=True)
class AIConfig:
    api_key: str = field(default='', repr=False)
    password: str = field(default='', repr=False)
    model: str = MODEL

    @property
    def ready(self):
        return bool(self.api_key) and len(self.password) >= 12 and self.model in ALLOWED_MODELS

    @property
    def revision(self):
        return hashlib.sha256(self.password.encode()).hexdigest()


def load_config(secret_getter=None, environ=None):
    env = os.environ if environ is None else environ
    def read(name):
        # O getter fornecido pela interface é exclusivamente st.secrets.get.
        try:
            value = secret_getter(name) if secret_getter else None
        except (KeyError, FileNotFoundError):
            value = None
        return str(value or env.get(name) or '').strip()
    return AIConfig(api_key=read('OPENAI_API_KEY'), password=read('INOVAMATCH_DEMO_PASSWORD'), model=read('OPENAI_MODEL') or MODEL)


@dataclass
class SessionAccess:
    authenticated_until: float = 0
    password_revision: str = ''
    failed_attempts: int = 0
    blocked_until: float = 0
    calls_used: int = 0
    usage: list = field(default_factory=list)

    def login(self, supplied, config, at=None):
        at = time.time() if at is None else at
        if at < self.blocked_until or not config.ready:
            return False
        if hmac.compare_digest(supplied.encode(), config.password.encode()):
            self.authenticated_until = at + AUTH_SECONDS
            self.password_revision = config.revision
            self.failed_attempts = 0
            return True
        self.failed_attempts += 1
        if self.failed_attempts >= 5:
            self.blocked_until = at + 300
            self.failed_attempts = 0
        return False

    def authorized(self, config, at=None):
        at = time.time() if at is None else at
        return config.ready and at < self.authenticated_until and hmac.compare_digest(self.password_revision, config.revision)

    def logout(self):
        self.authenticated_until = 0
        self.password_revision = ''
        # Sair não restaura a cota de chamadas desta sessão.
