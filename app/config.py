from pydantic import BaseModel


class AppConfig(BaseModel):
    api_base_url: str = "https://vkresult.ru/method"
    api_version: str = "5.124"
    max_depth_default: int = 11
    max_friends_per_user_default: int = 250
    max_root_friends_default: int = 5000
    api_delay_default: float = 0.34
    request_timeout: float = 20.0
    profile_batch_size: int = 200
    jsonp_callback: str = "jQuery22409162834852248698_1778000624926"
    cache_enabled_default: bool = True
    app_name: str = "VKHandshakes"
    barkov_base_url: str = "https://vk.barkov.net/"
    github_pages_auth_helper_url: str = "https://r7zex.github.io/vk_handshakes/auth-helper/"
    resolved_users_ttl_seconds: int = 7 * 24 * 60 * 60
    friends_cache_ttl_seconds: int = 24 * 60 * 60
    profile_cache_ttl_seconds: int = 7 * 24 * 60 * 60
    hub_cache_ttl_seconds: int = 7 * 24 * 60 * 60


CONFIG = AppConfig()
