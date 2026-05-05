from vk.errors import TokenRequiredError


class TokenManager:
    def __init__(self, token_store, token_provider, validate_callback):
        self.token_store = token_store
        self.token_provider = token_provider
        self.validate_callback = validate_callback
        self._token: str | None = None
        self._validated = False

    def validate_token(self, token: str) -> bool:
        try:
            return bool(self.validate_callback(token))
        except Exception:
            return False

    def get_valid_token(self) -> str:
        token = self._token or self.token_store.load_token() or self.token_provider.get_token()
        if not token:
            raise TokenRequiredError(None, "Токен не найден")

        if self._token == token and self._validated:
            return token

        if self.validate_token(token):
            self._token = token
            self._validated = True
            self.token_store.save_token(token)
            return token

        self.delete_token()
        new_token = self.token_provider.get_token()
        if not new_token or new_token == token or not self.validate_token(new_token):
            raise TokenRequiredError(5, "Нужна повторная авторизация")

        self.save_token(new_token)
        self._validated = True
        return new_token

    def refresh_or_reauth(self) -> str:
        self.invalidate_token()
        return self.get_valid_token()

    def invalidate_token(self) -> None:
        self.delete_token()

    def save_token(self, token: str) -> None:
        self._token = token
        self._validated = False
        self.token_store.save_token(token)

    def delete_token(self) -> None:
        self._token = None
        self._validated = False
        self.token_store.delete_token()

    def has_token(self) -> bool:
        return bool(self._token or self.token_store.load_token() or self.token_provider.get_token())
