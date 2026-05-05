from pathlib import Path
import keyring

from app.constants import APP_NAME
from storage.paths import get_app_data_dir


class TokenStore:
    SERVICE = APP_NAME
    USERNAME = "vk_access_token"

    def save_token(self, token: str) -> None:
        try:
            keyring.set_password(self.SERVICE, self.USERNAME, token)
        except Exception:
            (get_app_data_dir() / "token.txt").write_text(token, encoding="utf-8")

    def load_token(self) -> str | None:
        try:
            token = keyring.get_password(self.SERVICE, self.USERNAME)
            if token:
                return token
        except Exception:
            pass
        fallback = get_app_data_dir() / "token.txt"
        return fallback.read_text(encoding="utf-8").strip() if fallback.exists() else None

    def delete_token(self) -> None:
        try:
            keyring.delete_password(self.SERVICE, self.USERNAME)
        except Exception:
            pass
        fallback = get_app_data_dir() / "token.txt"
        if fallback.exists():
            fallback.unlink()
