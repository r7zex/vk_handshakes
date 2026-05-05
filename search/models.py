from pydantic import BaseModel, Field

from app.config import CONFIG


class SearchSettings(BaseModel):
    max_depth: int = CONFIG.max_depth_default
    max_friends_per_user: int = CONFIG.max_friends_per_user_default
    max_root_friends: int = CONFIG.max_root_friends_default
    api_delay: float = CONFIG.api_delay_default
    profile_batch_size: int = CONFIG.profile_batch_size
    forbid_direct_connection: bool = True
    filter_closed_profiles: bool = True
    exclude_hubs: bool = True
    use_cache: bool = CONFIG.cache_enabled_default


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
    filtered_profiles_count: int = 0
    hubs_count: int = 0


class SearchResult(BaseModel):
    found: bool
    path: list[int] = Field(default_factory=list)
    path_urls: list[str] = Field(default_factory=list)
    depth: int = 0
    message: str = ""
    processed_users: int = 0
    vk_requests_count: int = 0
    elapsed_seconds: float = 0.0
