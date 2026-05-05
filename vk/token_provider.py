from abc import ABC, abstractmethod


class TokenProvider(ABC):
    @abstractmethod
    def get_token(self) -> str | None:
        ...


class ManualTokenProvider(TokenProvider):
    def __init__(self, token: str | None = None):
        self._token = token

    def set_token(self, token: str) -> None:
        self._token = token

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
