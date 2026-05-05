from pydantic import BaseModel


class AppConfig(BaseModel):
    api_base_url: str = "https://api.vk.com/method"
    api_version: str = "5.199"
    max_depth_default: int = 4
    max_friends_per_user_default: int = 5000
    max_root_friends_default: int = 5000
    api_delay_default: float = 0.1
    request_timeout: float = 20.0
    profile_batch_size: int = 200
    jsonp_callback: str = "callback"
    cache_enabled_default: bool = True
    app_name: str = "VKHandshakes"


CONFIG = AppConfig()
