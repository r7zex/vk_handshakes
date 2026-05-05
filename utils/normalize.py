import re


def normalize_vk_input(user_input: str) -> str:
    value = user_input.strip()
    value = re.sub(r"^https?://", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^vk\.com/", "", value, flags=re.IGNORECASE)
    return value.strip("/")
