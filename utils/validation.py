from search.models import SearchSettings


def validate_search_form(
    user1: str,
    user2: str,
    settings: SearchSettings | None = None,
) -> list[str]:
    errors: list[str] = []

    if not user1.strip():
        errors.append("Первый пользователь не заполнен")
    if not user2.strip():
        errors.append("Второй пользователь не заполнен")
    if user1.strip() and user2.strip() and user1.strip() == user2.strip():
        errors.append("Пользователи должны быть разными")

    if settings:
        if settings.max_depth <= 0:
            errors.append("MAX_DEPTH должен быть больше 0")
        if settings.max_friends_per_user <= 0:
            errors.append("MAX_FRIENDS_PER_USER должен быть больше 0")
        if settings.max_root_friends <= 0:
            errors.append("MAX_ROOT_FRIENDS должен быть больше 0")
        if settings.api_delay < 0:
            errors.append("API_DELAY не может быть отрицательным")
        if settings.profile_batch_size <= 0:
            errors.append("PROFILE_BATCH_SIZE должен быть больше 0")

    return errors
