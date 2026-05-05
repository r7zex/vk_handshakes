from vk.errors import TokenRequiredError


class TokenManager:
    def __init__(self, token_store, token_provider):
        self.token_store = token_store
        self.token_provider = token_provider
        self._token: str | None = None

    def get_valid_token(self) -> str:
        token = self._token or self.token_store.load_token() or self.token_provider.get_token()
        if not token:
            raise TokenRequiredError(None, "Токен не найден")
        self._token = token
        return token

    def refresh_or_reauth(self) -> str:
        self.delete_token()
        return self.get_valid_token()

    def invalidate_token(self) -> None:
        self.delete_token()

    def save_token(self, token: str) -> None:
        self._token = token
        self.token_store.save_token(token)

    def delete_token(self) -> None:
        self._token = None
        self.token_store.delete_token()

    def has_token(self) -> bool:
        return bool(self._token or self.token_store.load_token())
