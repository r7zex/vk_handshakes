from dataclasses import dataclass


@dataclass
class AppState:
    authorized: bool = False
    current_user_id: int | None = None
    search_running: bool = False
    cancel_requested: bool = False
