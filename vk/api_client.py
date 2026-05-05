import time
import requests

from app.config import CONFIG
from app.constants import VK_RATE_LIMIT_CODES, VK_TOKEN_ERROR_CODES
from vk.errors import VkApiError, TokenExpiredError, VkRateLimitError


class VkApiClient:
    def __init__(self, token_manager, logger_callback=None):
        self.token_manager = token_manager
        self.logger = logger_callback or (lambda *_: None)
        self.requests_count = 0

    def call(self, method: str, params: dict | None = None):
        for _ in range(3):
            token = self.token_manager.get_valid_token()
            query = {"access_token": token, "v": CONFIG.api_version, **(params or {})}
            try:
                self.requests_count += 1
                r = requests.get(f"{CONFIG.api_base_url}/{method}", params=query, timeout=CONFIG.request_timeout)
                data = r.json()
            except requests.RequestException as exc:
                self.logger("warning", f"[vk] network retry: {exc}")
                time.sleep(1)
                continue
            if "response" in data:
                return data["response"]
            err = data.get("error", {})
            code = err.get("error_code")
            msg = err.get("error_msg", "VK API error")
            if code in VK_RATE_LIMIT_CODES:
                time.sleep(1)
                continue
            if code in VK_TOKEN_ERROR_CODES:
                self.token_manager.invalidate_token()
                raise TokenExpiredError(code, msg, data)
            raise VkApiError(code, msg, data)
        raise VkRateLimitError(29, "Too many requests")

    def users_get(self, user_ids: str | int, fields: str = ""):
        return self.call("users.get", {"user_ids": user_ids, "fields": fields})

    def friends_get_direct(self, user_id: int, count: int, offset: int = 0):
        return self.call("friends.get", {"user_id": user_id, "count": count, "offset": offset})
