from pydantic import BaseModel


class SearchSettings(BaseModel):
    max_depth: int = 4
    max_friends_per_user: int = 5000
    max_root_friends: int = 5000
    api_delay: float = 0.1
    profile_batch_size: int = 200
    forbid_direct_connection: bool = False
    filter_closed_profiles: bool = True
    exclude_hubs: bool = False
    use_cache: bool = True


class SearchProgress(BaseModel):
    event_type: str
    message: str
    user_id: int | None = None
    depth: int | None = None
    direction: str | None = None
    frontier_fwd_size: int | None = None
    frontier_bwd_size: int | None = None
    processed_users: int = 0
    vk_requests_count: int = 0


class SearchResult(BaseModel):
    found: bool
    path: list[int] = []
    path_urls: list[str] = []
    depth: int = 0
    message: str = ""
    processed_users: int = 0
    vk_requests_count: int = 0
    elapsed_seconds: float = 0.0
