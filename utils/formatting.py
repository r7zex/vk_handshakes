def format_user_url(user_id: int) -> str:
    return f"https://vk.com/id{user_id}"


def format_path(path: list[int]) -> str:
    return " -> ".join(format_user_url(uid) for uid in path)


def format_elapsed(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def mask_token(token: str) -> str:
    if len(token) <= 10:
        return "***"
    return f"{token[:7]}...{token[-3:]}"
