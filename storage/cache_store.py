from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from app.config import CONFIG
from storage.paths import get_cache_path


class CacheStore:
    def __init__(self):
        self.path = get_cache_path()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init_db(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS resolved_users (
                    input TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS friends_cache (
                    user_id INTEGER NOT NULL,
                    force INTEGER NOT NULL,
                    friends_json TEXT NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (user_id, force)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_cache (
                    user_id INTEGER PRIMARY KEY,
                    profile_json TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS hub_cache (
                    user_id INTEGER PRIMARY KEY,
                    is_hub INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )

    @staticmethod
    def _fresh(updated_at: int, ttl_seconds: int) -> bool:
        return int(time.time()) - updated_at <= ttl_seconds

    def get_resolved_user(self, raw_input: str) -> int | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT user_id, updated_at FROM resolved_users WHERE input = ?",
                (raw_input,),
            ).fetchone()
        if not row or not self._fresh(row[1], CONFIG.resolved_users_ttl_seconds):
            return None
        return int(row[0])

    def save_resolved_user(self, raw_input: str, user_id: int) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT OR REPLACE INTO resolved_users (input, user_id, updated_at)
                VALUES (?, ?, ?)
                """,
                (raw_input, user_id, int(time.time())),
            )

    def get_friends(self, user_id: int, force: bool) -> list[int] | None:
        with self._connect() as con:
            row = con.execute(
                """
                SELECT friends_json, updated_at
                FROM friends_cache
                WHERE user_id = ? AND force = ?
                """,
                (user_id, int(force)),
            ).fetchone()
        if not row or not self._fresh(row[1], CONFIG.friends_cache_ttl_seconds):
            return None
        try:
            return [int(uid) for uid in json.loads(row[0])]
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def save_friends(self, user_id: int, force: bool, friends: list[int]) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT OR REPLACE INTO friends_cache
                    (user_id, force, friends_json, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, int(force), json.dumps(friends), int(time.time())),
            )

    def get_profile(self, user_id: int) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT profile_json, updated_at FROM profile_cache WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row or not self._fresh(row[1], CONFIG.profile_cache_ttl_seconds):
            return None
        try:
            profile = json.loads(row[0])
        except (TypeError, json.JSONDecodeError):
            return None
        return profile if isinstance(profile, dict) else None

    def save_profile(self, user_id: int, profile: dict[str, Any]) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT OR REPLACE INTO profile_cache
                    (user_id, profile_json, updated_at)
                VALUES (?, ?, ?)
                """,
                (user_id, json.dumps(profile, ensure_ascii=False), int(time.time())),
            )

    def is_hub(self, user_id: int) -> bool | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT is_hub, updated_at FROM hub_cache WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row or not self._fresh(row[1], CONFIG.hub_cache_ttl_seconds):
            return None
        return bool(row[0])

    def save_hub(self, user_id: int, is_hub: bool) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT OR REPLACE INTO hub_cache (user_id, is_hub, updated_at)
                VALUES (?, ?, ?)
                """,
                (user_id, int(is_hub), int(time.time())),
            )

    def clear_cache(self) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM resolved_users")
            con.execute("DELETE FROM friends_cache")
            con.execute("DELETE FROM profile_cache")
            con.execute("DELETE FROM hub_cache")
