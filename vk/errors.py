class VkApiError(Exception):
    def __init__(self, code: int | None, message: str, raw: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.raw = raw or {}


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
