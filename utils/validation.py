def validate_search_form(user1: str, user2: str) -> list[str]:
    errors: list[str] = []
    if not user1.strip():
        errors.append("Первый пользователь не заполнен")
    if not user2.strip():
        errors.append("Второй пользователь не заполнен")
    if user1.strip() and user2.strip() and user1.strip() == user2.strip():
        errors.append("Пользователи должны быть разными")
    return errors
