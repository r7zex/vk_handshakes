from PySide6.QtCore import QObject, Signal, Slot

from search.bfs import bidirectional_bfs
from search.models import SearchResult
from vk.errors import SearchCancelledError
from vk.user_resolver import resolve_blacklist, resolve_user_id


class SearchWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        client,
        friends_service,
        start_value: str,
        end_value: str,
        settings,
        ignored_profiles_raw: str,
        cache_store=None,
    ):
        super().__init__()
        self.client = client
        self.friends_service = friends_service
        self.start_value = start_value
        self.end_value = end_value
        self.ignored_profiles_raw = ignored_profiles_raw
        self.settings = settings
        self.cache_store = cache_store
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def _cancelled(self) -> bool:
        return self._cancel

    @Slot()
    def run(self) -> None:
        try:
            self.client.logger = lambda _level, message: self.progress.emit(message)
            self.client.api_delay = self.settings.api_delay
            self.progress.emit("[search] Разрешаем пользователей...")

            cache_store = self.cache_store if self.settings.use_cache else None
            start_id = resolve_user_id(
                self.client,
                self.start_value,
                cache_store,
                self.progress.emit,
            )
            end_id = resolve_user_id(
                self.client,
                self.end_value,
                cache_store,
                self.progress.emit,
            )

            if start_id is None or end_id is None:
                raise ValueError("Не удалось разрешить один или оба VK ID")

            if self._cancelled():
                raise SearchCancelledError()

            self.progress.emit(f"[search] Старт: https://vk.com/id{start_id}")
            self.progress.emit(f"[search] Финиш: https://vk.com/id{end_id}")

            ignored_profiles = resolve_blacklist(
                self.client,
                self.ignored_profiles_raw,
                cache_store,
                self.progress.emit,
            )

            result = bidirectional_bfs(
                self.client,
                self.friends_service,
                start_id,
                end_id,
                self.settings,
                ignored_profiles,
                progress_callback=self.progress.emit,
                cancel_checker=self._cancelled,
            )
            self.finished.emit(result)

        except SearchCancelledError:
            self.finished.emit(
                SearchResult(
                    found=False,
                    message="Поиск остановлен пользователем",
                    vk_requests_count=self.client.requests_count,
                )
            )

        except Exception as exc:
            self.failed.emit(str(exc))
