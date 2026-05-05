import re
from abc import ABC, abstractmethod
from urllib.parse import parse_qs, urlparse


def extract_token(raw: str) -> str | None:
    value = raw.strip()

    if not value or value.startswith("#"):
        return None

    if "access_token=" in value:
        try:
            parsed = urlparse(value)
            fragment_params = parse_qs(parsed.fragment)
            query_params = parse_qs(parsed.query)
            token = (
                fragment_params.get("access_token", [None])[0]
                or query_params.get("access_token", [None])[0]
            )
            if token:
                return token
        except Exception:
            pass

        match = re.search(r"access_token=([a-zA-Z0-9_.\-]+)", value)
        if match:
            return match.group(1)

        return None

    if re.fullmatch(r"[a-zA-Z0-9_.\-]+", value):
        return value

    return None


class TokenProvider(ABC):
    @abstractmethod
    def get_token(self) -> str | None:
        ...


class ManualTokenProvider(TokenProvider):
    def __init__(self, token: str | None = None):
        self._token = extract_token(token) if token else None

    def set_token(self, token: str) -> None:
        self._token = extract_token(token)

    def get_token(self) -> str | None:
        return self._token


class BrowserAuthTokenProvider(TokenProvider):
    def get_token(self) -> str | None:
        return None


class LocalSessionTokenProvider(TokenProvider):
    def __init__(self, token_store):
        self.token_store = token_store

    def get_token(self) -> str | None:
        return self.token_store.load_token()
