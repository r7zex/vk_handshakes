def format_user_url(user_id: int) -> str:
    return f"https://vk.com/id{user_id}"


def format_path(path: list[int]) -> str:
    return " → ".join(format_user_url(uid) for uid in path)


def mask_token(token: str) -> str:
    if len(token) <= 12:
        return "***"
    return f"{token[:8]}...{token[-4:]}"
