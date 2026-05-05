from utils.normalize import normalize_vk_input


def resolve_user_id(client, value: str) -> int:
    n = normalize_vk_input(value)
    if n.isdigit():
        return int(n)
    if n.startswith("id") and n[2:].isdigit():
        return int(n[2:])
    user = client.users_get(n)[0]
    return int(user["id"])


def resolve_blacklist(client, raw: str) -> set[int]:
    result: set[int] = set()
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        result.add(resolve_user_id(client, line))
    return result


def get_user_url(user_id: int) -> str:
    return f"https://vk.com/id{user_id}"
