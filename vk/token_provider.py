import re
from abc import ABC, abstractmethod
from urllib.parse import parse_qs, urlparse

from vk.barkov_token_flow import BarkovTokenAcquirer, BarkovTokenRequest


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


class BarkovTokenProvider(TokenProvider):
    """Automatic token provider scaffold.

    TokenManager already calls TokenProvider.get_token() when the saved token is
    absent or invalid. After vk.barkov.net browser automation is implemented in
    BarkovTokenAcquirer, this provider will become the automatic fallback.
    """

    def __init__(self, acquirer: BarkovTokenAcquirer | None = None, logger_callback=None):
        self.acquirer = acquirer or BarkovTokenAcquirer(logger_callback)
        self.logger = logger_callback or (lambda *_: None)
        self.preferred_vk_profile: str | None = None

    def set_preferred_vk_profile(self, value: str | None) -> None:
        self.preferred_vk_profile = value.strip() if value and value.strip() else None

    def get_token(self) -> str | None:
        result = self.acquirer.acquire_token(
            BarkovTokenRequest(vk_profile_input=self.preferred_vk_profile)
        )
        if result.ok:
            return result.access_token
        if result.error:
            self.logger("warning", f"[auth] {result.error}")
        return None


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


class BrowserAuthTokenProvider(BarkovTokenProvider):
    """Backward-compatible name for the automatic browser provider."""


class LocalSessionTokenProvider(TokenProvider):
    def __init__(self, token_store):
        self.token_store = token_store

    def get_token(self) -> str | None:
        return self.token_store.load_token()
