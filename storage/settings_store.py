import json
from search.models import SearchSettings
from storage.paths import get_settings_path


class SettingsStore:
    def load_settings(self) -> SearchSettings:
        path = get_settings_path()
        if not path.exists():
            return SearchSettings()
        return SearchSettings.model_validate_json(path.read_text(encoding="utf-8"))

    def save_settings(self, settings: SearchSettings) -> None:
        get_settings_path().write_text(settings.model_dump_json(indent=2), encoding="utf-8")

    def reset_settings(self) -> SearchSettings:
        settings = SearchSettings()
        self.save_settings(settings)
        return settings
