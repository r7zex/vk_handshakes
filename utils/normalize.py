import re


def normalize_vk_input(user_input: str) -> str:
    value = user_input.strip()
    value = re.sub(r"^https?://", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^vk\.com/", "", value, flags=re.IGNORECASE)
    value = value.split("?", 1)[0].split("#", 1)[0].strip("/")

    if value.startswith("id") and value[2:].isdigit():
        return value[2:]

    return value
