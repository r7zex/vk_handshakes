from vk.errors import TokenRequiredError


class TokenManager:
    def __init__(self, token_store, token_provider, validate_callback):
        self.token_store = token_store
        self.token_provider = token_provider
        self.validate_callback = validate_callback

    def validate_token(self, token: str) -> bool:
        return self.validate_callback(token)

    def get_valid_token(self) -> str:
        token = self.token_store.load_token() or self.token_provider.get_token()
        if not token:
            raise TokenRequiredError(None, "Токен не найден")
        if self.validate_token(token):
            self.token_store.save_token(token)
            return token
        self.delete_token()
        new_token = self.token_provider.get_token()
        if not new_token or not self.validate_token(new_token):
            raise TokenRequiredError(5, "Нужна повторная авторизация")
        self.save_token(new_token)
        return new_token

    def refresh_or_reauth(self) -> str:
        self.invalidate_token()
        return self.get_valid_token()

    def invalidate_token(self) -> None:
        self.delete_token()

    def save_token(self, token: str) -> None:
        self.token_store.save_token(token)

    def delete_token(self) -> None:
        self.token_store.delete_token()
