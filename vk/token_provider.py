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

    def discard_token(self, token: str) -> None:
        if self._token == token:
            self._token = None


class CompositeTokenProvider(TokenProvider):
    def __init__(self, providers: list[TokenProvider]):
        self.providers = providers

    def get_token(self) -> str | None:
        for provider in self.providers:
            token = provider.get_token()
            if token:
                return token
        return None

    def discard_token(self, token: str) -> None:
        for provider in self.providers:
            discard = getattr(provider, "discard_token", None)
            if discard:
                discard(token)
