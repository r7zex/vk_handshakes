from __future__ import annotations

import json
import re
import time
from typing import Any, cast

import requests

from app.config import CONFIG
from app.constants import VK_RATE_LIMIT_CODES, VK_TOKEN_ERROR_CODES
from vk.errors import TokenExpiredError, VkApiError, VkRateLimitError


def parse_jsonp(text: str) -> dict[str, Any]:
    value = text.strip()

    if value.startswith("{"):
        return cast(dict[str, Any], json.loads(value))

    match = re.match(r"^[^(]+\((.*)\);?$", value, flags=re.DOTALL)
    if not match:
        raise RuntimeError(f"Не удалось распарсить JSONP: {value[:200]}")

    return cast(dict[str, Any], json.loads(match.group(1)))


class VkApiClient:
    ROTATE_ON_CODES: frozenset[int] = frozenset(VK_TOKEN_ERROR_CODES)
    WAIT_AND_RETRY_CODES: frozenset[int] = frozenset(VK_RATE_LIMIT_CODES)

    def __init__(self, token_manager, logger_callback=None):
        self.token_manager = token_manager
        self.logger = logger_callback or (lambda *_: None)
        self.requests_count = 0
        self.session = requests.Session()
        self.api_delay = CONFIG.api_delay_default

    def _should_use_jsonp(self) -> bool:
        return "vkresult.ru" in CONFIG.api_base_url.lower()

    def call(self, method: str, params: dict | None = None) -> Any:
        request_params = dict(params or {})
        url = f"{CONFIG.api_base_url}/{method}"
        rate_attempts = 0
        network_attempts = 0
        token_attempts = 0

        while True:
            token = self.token_manager.get_valid_token()
            query = dict(request_params)
            query["access_token"] = token
            query["v"] = CONFIG.api_version

            if self._should_use_jsonp():
                query["callback"] = CONFIG.jsonp_callback
                query["_"] = str(int(time.time() * 1000))

            if self.api_delay > 0:
                time.sleep(self.api_delay)

            try:
                self.requests_count += 1
                self.logger("info", f"[vk] {method}")
                response = self.session.get(
                    url,
                    params=query,
                    timeout=CONFIG.request_timeout,
                )
                response.raise_for_status()
                data = parse_jsonp(response.text) if self._should_use_jsonp() else response.json()

            except requests.RequestException as exc:
                network_attempts += 1
                if network_attempts > 5:
                    raise RuntimeError(f"HTTP-ошибка при запросе {method}: {exc}") from exc
                wait_seconds = min(2 + network_attempts * 2, 15)
                self.logger("warning", f"[network] {exc}. Ждём {wait_seconds} сек...")
                time.sleep(wait_seconds)
                continue

            except (json.JSONDecodeError, RuntimeError) as exc:
                raise RuntimeError(f"VK API вернул плохой ответ для {method}: {exc}") from exc

            if "response" in data:
                return data["response"]

            if "error" not in data:
                raise RuntimeError(f"Неожиданный ответ VK API: {data}")

            error = data["error"]
            code = int(error.get("error_code", -1))
            message = error.get("error_msg", "unknown error")

            if code in self.WAIT_AND_RETRY_CODES:
                rate_attempts += 1
                if rate_attempts > 8:
                    raise VkRateLimitError(code, message, data)
                wait_seconds = min(2 + rate_attempts, 10)
                self.logger("warning", f"[rate] {code}: {message}. Ждём {wait_seconds} сек...")
                time.sleep(wait_seconds)
                continue

            if code in self.ROTATE_ON_CODES:
                token_attempts += 1
                self.logger("warning", f"[token] {code}: {message}. Требуется новый токен.")
                if token_attempts > 2:
                    raise TokenExpiredError(code, message, data)
                self.token_manager.refresh_or_reauth()
                continue

            raise VkApiError(code, message, data)

    def users_get(self, user_ids: str | int, fields: str = "") -> list[dict[str, Any]]:
        params: dict[str, Any] = {"user_ids": str(user_ids)}
        if fields:
            params["fields"] = fields

        response = self.call("users.get", params)
        if not isinstance(response, list):
            raise RuntimeError(f"Ожидался список от users.get, получено: {response}")

        return cast(list[dict[str, Any]], response)

    def users_get_batch(
        self,
        user_ids: list[int],
        fields: str = "can_access_closed,deactivated,is_closed",
        batch_size: int = CONFIG.profile_batch_size,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        for index in range(0, len(user_ids), batch_size):
            chunk = user_ids[index : index + batch_size]
            ids_str = ",".join(map(str, chunk))
            try:
                result.extend(self.users_get(ids_str, fields=fields))
            except Exception as exc:
                self.logger("warning", f"[warn] users.get batch ошибка: {exc}")

        return result

    def friends_get_execute(self, user_id: int, count: int, offset: int = 0) -> dict[str, Any]:
        code = (
            "return ["
            "{"
            f"u:{user_id},"
            '"m":"fr",'
            f"o:{offset},"
            f"d:API.friends.get({{user_id:{user_id},count:{count},offset:{offset}}})"
            "}"
            "];"
        )

        response = self.call("execute", {"code": code})
        if not isinstance(response, list) or not response:
            raise RuntimeError(f"Некорректный ответ execute: {response}")

        item = response[0]
        if not isinstance(item, dict):
            raise RuntimeError(f"Некорректный элемент execute: {item}")

        data = item.get("d")
        if data is False:
            return {
                "count": 0,
                "items": [],
                "_execute_failed": True,
                "_user_id": user_id,
                "_offset": offset,
            }

        if not isinstance(data, dict):
            raise RuntimeError(f"Некорректное поле d в execute: {item}")

        return cast(dict[str, Any], data)

    def friends_get_direct(self, user_id: int, count: int, offset: int = 0) -> dict[str, Any]:
        response = self.call(
            "friends.get",
            {"user_id": user_id, "count": count, "offset": offset},
        )

        if not isinstance(response, dict):
            raise RuntimeError(f"Некорректный ответ friends.get: {response}")

        return cast(dict[str, Any], response)
