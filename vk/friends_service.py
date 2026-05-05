from __future__ import annotations

from typing import Any

from app.constants import PRIVATE_PROFILE_ERROR_CODES
from search.models import SearchSettings
from vk.errors import SearchCancelledError, VkApiError


def is_profile_open(profile: dict[str, Any]) -> bool:
    if profile.get("deactivated"):
        return False

    if profile.get("is_closed") and not profile.get("can_access_closed"):
        return False

    return True


class FriendsService:
    def __init__(self, client, cache_store=None, logger_callback=None):
        self.client = client
        self.cache_store = cache_store
        self.logger = logger_callback or (lambda *_: None)
        self.filtered_profiles_count = 0
        self.hubs_count = 0

    def _progress(self, callback, message: str) -> None:
        if callback:
            callback(message)
        else:
            self.logger("info", message)

    @staticmethod
    def _check_cancel(cancel_checker) -> None:
        if cancel_checker and cancel_checker():
            raise SearchCancelledError()

    def batch_check_profiles(
        self,
        user_ids: list[int],
        profile_cache: dict[int, dict[str, Any]],
        settings: SearchSettings,
        progress_callback=None,
        cancel_checker=None,
    ) -> None:
        unchecked: list[int] = []

        for uid in user_ids:
            self._check_cancel(cancel_checker)
            if uid in profile_cache:
                continue
            if settings.use_cache and self.cache_store:
                cached = self.cache_store.get_profile(uid)
                if cached is not None:
                    profile_cache[uid] = cached
                    continue
            unchecked.append(uid)

        if not unchecked:
            return

        profiles = self.client.users_get_batch(
            unchecked,
            fields="can_access_closed,deactivated,is_closed",
            batch_size=settings.profile_batch_size,
        )

        for profile in profiles:
            uid = int(profile["id"])
            profile_cache[uid] = profile
            if settings.use_cache and self.cache_store:
                self.cache_store.save_profile(uid, profile)

        returned_ids = {int(profile["id"]) for profile in profiles}
        for uid in unchecked:
            if uid not in returned_ids:
                profile = {"id": uid, "deactivated": "deleted"}
                profile_cache[uid] = profile
                if settings.use_cache and self.cache_store:
                    self.cache_store.save_profile(uid, profile)

        self._progress(
            progress_callback,
            f"[vk] users.get batch: проверено {len(unchecked)} профилей",
        )

    def get_friends(
        self,
        user_id: int,
        settings: SearchSettings,
        force: bool = False,
        hub_cache: set[int] | None = None,
        friends_cache: dict[tuple[int, bool], list[int]] | None = None,
        profile_cache: dict[int, dict[str, Any]] | None = None,
        progress_callback=None,
        cancel_checker=None,
    ) -> list[int]:
        self._check_cancel(cancel_checker)
        hub_cache = hub_cache if hub_cache is not None else set()
        friends_cache = friends_cache if friends_cache is not None else {}
        profile_cache = profile_cache if profile_cache is not None else {}
        cache_key = (user_id, force)

        if cache_key in friends_cache:
            return friends_cache[cache_key]

        if settings.use_cache and self.cache_store:
            cached = self.cache_store.get_friends(user_id, force)
            if cached is not None:
                friends_cache[cache_key] = cached
                return cached

        try:
            count_to_load = settings.max_root_friends if force else settings.max_friends_per_user
            response = self.client.friends_get_execute(
                user_id=user_id,
                count=count_to_load,
                offset=0,
            )

            if response.get("_execute_failed"):
                self._progress(
                    progress_callback,
                    f"[fallback] uid={user_id} — execute вернул false, пробуем friends.get",
                )
                try:
                    response = self.client.friends_get_direct(
                        user_id=user_id,
                        count=count_to_load,
                        offset=0,
                    )
                except VkApiError as exc:
                    self._skip_private(
                        user_id,
                        exc,
                        cache_key,
                        friends_cache,
                        settings,
                        progress_callback,
                    )
                    return []

            total = int(response.get("count", 0))
            items = response.get("items", [])
            if not isinstance(items, list):
                items = []

            if settings.exclude_hubs and not force and total > settings.max_friends_per_user:
                hub_cache.add(user_id)
                self.hubs_count += 1
                if settings.use_cache and self.cache_store:
                    self.cache_store.save_hub(user_id, True)
                self._progress(
                    progress_callback,
                    f"[hub] uid={user_id} — {total} друзей, исключён",
                )
                friends_cache[cache_key] = []
                return []

            raw_friends = [int(uid) for uid in items]

            if raw_friends and settings.filter_closed_profiles:
                self.batch_check_profiles(
                    raw_friends,
                    profile_cache,
                    settings,
                    progress_callback=progress_callback,
                    cancel_checker=cancel_checker,
                )
                friends = [
                    uid for uid in raw_friends if is_profile_open(profile_cache.get(uid, {}))
                ]
            else:
                friends = raw_friends

            skipped = len(raw_friends) - len(friends)
            if skipped > 0:
                self.filtered_profiles_count += skipped
                self._progress(
                    progress_callback,
                    (
                        f"[filter] uid={user_id} — отсеяно {skipped} "
                        f"закрытых/удалённых профилей из {len(raw_friends)}"
                    ),
                )

            friends_cache[cache_key] = friends
            if settings.use_cache and self.cache_store:
                self.cache_store.save_friends(user_id, force, friends)

            self._progress(
                progress_callback,
                f"[vk] friends.get uid={user_id}: {len(friends)} доступных друзей",
            )
            return friends

        except VkApiError as exc:
            self._skip_private(
                user_id,
                exc,
                cache_key,
                friends_cache,
                settings,
                progress_callback,
            )
            return []

        except SearchCancelledError:
            raise

        except Exception as exc:
            self._progress(progress_callback, f"[skip] uid={user_id} — {exc}")
            friends_cache[cache_key] = []
            return []

    def _skip_private(
        self,
        user_id: int,
        exc: VkApiError,
        cache_key: tuple[int, bool],
        friends_cache: dict[tuple[int, bool], list[int]],
        settings: SearchSettings,
        progress_callback=None,
    ) -> None:
        reasons = {
            15: "профиль закрыт",
            18: "страница удалена",
            30: "профиль приватный",
        }
        if exc.code in PRIVATE_PROFILE_ERROR_CODES:
            message = reasons.get(exc.code, f"код {exc.code}: {exc.message}")
        else:
            message = f"код {exc.code}: {exc.message}"
        self._progress(progress_callback, f"[skip] uid={user_id} — {message}")
        friends_cache[cache_key] = []
        if settings.use_cache and self.cache_store:
            self.cache_store.save_friends(user_id, cache_key[1], [])

    def probe_is_hub(
        self,
        user_id: int,
        settings: SearchSettings,
        hub_cache: set[int],
        progress_callback=None,
        cancel_checker=None,
    ) -> bool:
        self._check_cancel(cancel_checker)

        if user_id in hub_cache:
            return True

        if settings.use_cache and self.cache_store:
            cached = self.cache_store.is_hub(user_id)
            if cached is not None:
                if cached:
                    hub_cache.add(user_id)
                return cached

        try:
            response = self.client.friends_get_execute(user_id=user_id, count=1, offset=0)
            if response.get("_execute_failed"):
                return False

            total = int(response.get("count", 0))
            is_hub = total > settings.max_friends_per_user
            if is_hub:
                hub_cache.add(user_id)
                self.hubs_count += 1
                self._progress(
                    progress_callback,
                    f"[hub] uid={user_id} — {total} друзей, отклонён как точка встречи",
                )

            if settings.use_cache and self.cache_store:
                self.cache_store.save_hub(user_id, is_hub)

            return is_hub

        except VkApiError:
            return False

        except Exception:
            return False
