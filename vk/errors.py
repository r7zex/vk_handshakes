class VkApiError(Exception):
    def __init__(self, code: int | None, message: str, raw: dict | None = None):
        self.code = code
        self.message = message
        self.raw = raw or {}
        prefix = f"VK API error {code}" if code is not None else "VK API error"
        super().__init__(f"{prefix}: {message}")


class TokenExpiredError(VkApiError):
    pass


class TokenRequiredError(VkApiError):
    pass


class VkRateLimitError(VkApiError):
    pass


class VkPrivateProfileError(VkApiError):
    pass


class SearchCancelledError(Exception):
    pass
