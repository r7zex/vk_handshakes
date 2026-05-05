from pathlib import Path
import os


def get_app_data_dir() -> Path:
    base = os.getenv("APPDATA") or str(Path.home() / ".config")
    path = Path(base) / "VKHandshakes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_settings_path() -> Path:
    return get_app_data_dir() / "settings.json"


def get_cache_path() -> Path:
    return get_app_data_dir() / "cache.sqlite"


def get_logs_dir() -> Path:
    path = get_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
