from collections.abc import Iterable

from utils.normalize import normalize_vk_input
from vk.errors import VkApiError


def resolve_user_id(client, value: str, cache_store=None, logger_callback=None) -> int | None:
    normalized = normalize_vk_input(value)
    if not normalized:
        return None

    if cache_store:
        cached = cache_store.get_resolved_user(normalized)
        if cached is not None:
            return cached

    try:
        response = client.users_get(
            normalized,
            fields="followers_count,can_access_closed,is_closed",
        )
        if not response:
            return None
        user_id = int(response[0]["id"])

        if cache_store:
            cache_store.save_resolved_user(normalized, user_id)
        return user_id

    except VkApiError as exc:
        if logger_callback:
            logger_callback(f"[error] Не удалось разрешить '{normalized}': {exc}")
        return None

    except Exception as exc:
        if logger_callback:
            logger_callback(f"[error] Не удалось разрешить '{normalized}': {exc}")
        return None


def resolve_blacklist(
    client,
    raw: str | Iterable[str],
    cache_store=None,
    logger_callback=None,
) -> set[int]:
    result: set[int] = set()

    if isinstance(raw, str):
        entries = raw.splitlines()
    else:
        entries = list(raw)

    entries = [entry.strip() for entry in entries if entry.strip()]
    if not entries:
        return result

    if logger_callback:
        logger_callback(f"[search] Разрешаем чёрный список: {len(entries)} записей")

    for entry in entries:
        uid = resolve_user_id(client, entry, cache_store, logger_callback)
        if uid is not None:
            result.add(uid)
            if logger_callback:
                logger_callback(f"[search] blacklist: {entry} → id{uid}")
        elif logger_callback:
            logger_callback(f"[warning] blacklist: {entry} не удалось разрешить")

    return result


def get_user_url(user_id: int) -> str:
    return f"https://vk.com/id{user_id}"
