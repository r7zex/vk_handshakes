from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from app.config import CONFIG
from storage.paths import get_cache_path


class CacheStore:
    SQLITE_CHUNK_SIZE = 900

    def __init__(self):
        self.path = get_cache_path()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30.0)
        con.execute("PRAGMA busy_timeout=30000")
        return con

    def _init_db(self) -> None:
        try:
            with self._connect() as con:
                con.execute("PRAGMA journal_mode=WAL")
                self._create_tables(con)
        except sqlite3.DatabaseError:
            self._reset_broken_db()
            with self._connect() as con:
                con.execute("PRAGMA journal_mode=WAL")
                self._create_tables(con)

    @staticmethod
    def _create_tables(con: sqlite3.Connection) -> None:
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
            CREATE TABLE IF NOT EXISTS friends_cache_v2 (
                user_id INTEGER NOT NULL,
                force INTEGER NOT NULL,
                limit_key INTEGER NOT NULL,
                friends_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, force, limit_key)
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
            CREATE TABLE IF NOT EXISTS hub_cache_v2 (
                user_id INTEGER NOT NULL,
                limit_key INTEGER NOT NULL,
                is_hub INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, limit_key)
            )
            """
        )

    def _reset_broken_db(self) -> None:
        broken_path = self.path.with_suffix(f".broken-{int(time.time())}.sqlite")
        try:
            if self.path.exists():
                self.path.replace(broken_path)
        except OSError:
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _fresh(updated_at: int, ttl_seconds: int) -> bool:
        return int(time.time()) - updated_at <= ttl_seconds

    @staticmethod
    def _chunks(values: list[int], chunk_size: int):
        for index in range(0, len(values), chunk_size):
            yield values[index : index + chunk_size]

    def get_resolved_user(self, raw_input: str) -> int | None:
        try:
            with self._connect() as con:
                row = con.execute(
                    "SELECT user_id, updated_at FROM resolved_users WHERE input = ?",
                    (raw_input,),
                ).fetchone()
        except sqlite3.DatabaseError:
            return None
        if not row or not self._fresh(row[1], CONFIG.resolved_users_ttl_seconds):
            return None
        return int(row[0])

    def save_resolved_user(self, raw_input: str, user_id: int) -> None:
        try:
            with self._connect() as con:
                con.execute(
                    """
                    INSERT OR REPLACE INTO resolved_users (input, user_id, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (raw_input, user_id, int(time.time())),
                )
        except sqlite3.DatabaseError:
            return

    def get_friends(
        self,
        user_id: int,
        force: bool,
        limit_key: int = 0,
    ) -> list[int] | None:
        try:
            with self._connect() as con:
                row = con.execute(
                    """
                    SELECT friends_json, updated_at
                    FROM friends_cache_v2
                    WHERE user_id = ? AND force = ? AND limit_key = ?
                    """,
                    (user_id, int(force), limit_key),
                ).fetchone()
        except sqlite3.DatabaseError:
            return None
        if not row or not self._fresh(row[1], CONFIG.friends_cache_ttl_seconds):
            return None
        try:
            return [int(uid) for uid in json.loads(row[0])]
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def save_friends(
        self,
        user_id: int,
        force: bool,
        limit_key: int,
        friends: list[int],
    ) -> None:
        try:
            with self._connect() as con:
                con.execute(
                    """
                    INSERT OR REPLACE INTO friends_cache_v2
                        (user_id, force, limit_key, friends_json, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        int(force),
                        limit_key,
                        json.dumps(friends),
                        int(time.time()),
                    ),
                )
        except sqlite3.DatabaseError:
            return

    def get_profile(self, user_id: int) -> dict[str, Any] | None:
        profiles = self.get_profiles([user_id])
        return profiles.get(user_id)

    def get_profiles(self, user_ids: list[int]) -> dict[int, dict[str, Any]]:
        if not user_ids:
            return {}

        result: dict[int, dict[str, Any]] = {}
        unique_ids = list(dict.fromkeys(int(uid) for uid in user_ids))

        try:
            with self._connect() as con:
                for chunk in self._chunks(unique_ids, self.SQLITE_CHUNK_SIZE):
                    placeholders = ",".join("?" for _ in chunk)
                    rows = con.execute(
                        f"""
                        SELECT user_id, profile_json, updated_at
                        FROM profile_cache
                        WHERE user_id IN ({placeholders})
                        """,
                        chunk,
                    ).fetchall()

                    for user_id, profile_json, updated_at in rows:
                        if not self._fresh(updated_at, CONFIG.profile_cache_ttl_seconds):
                            continue
                        try:
                            profile = json.loads(profile_json)
                        except (TypeError, json.JSONDecodeError):
                            continue
                        if isinstance(profile, dict):
                            result[int(user_id)] = profile
        except sqlite3.DatabaseError:
            return {}

        return result

    def save_profile(self, user_id: int, profile: dict[str, Any]) -> None:
        self.save_profiles({user_id: profile})

    def save_profiles(self, profiles: dict[int, dict[str, Any]]) -> None:
        if not profiles:
            return

        now = int(time.time())
        rows = [
            (int(user_id), json.dumps(profile, ensure_ascii=False), now)
            for user_id, profile in profiles.items()
        ]

        try:
            with self._connect() as con:
                con.executemany(
                    """
                    INSERT OR REPLACE INTO profile_cache
                        (user_id, profile_json, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    rows,
                )
        except sqlite3.DatabaseError:
            return

    def is_hub(self, user_id: int, limit_key: int = 0) -> bool | None:
        try:
            with self._connect() as con:
                row = con.execute(
                    """
                    SELECT is_hub, updated_at
                    FROM hub_cache_v2
                    WHERE user_id = ? AND limit_key = ?
                    """,
                    (user_id, limit_key),
                ).fetchone()
        except sqlite3.DatabaseError:
            return None
        if not row or not self._fresh(row[1], CONFIG.hub_cache_ttl_seconds):
            return None
        return bool(row[0])

    def save_hub(self, user_id: int, limit_key: int, is_hub: bool) -> None:
        try:
            with self._connect() as con:
                con.execute(
                    """
                    INSERT OR REPLACE INTO hub_cache_v2
                        (user_id, limit_key, is_hub, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, limit_key, int(is_hub), int(time.time())),
                )
        except sqlite3.DatabaseError:
            return

    def clear_cache(self) -> None:
        try:
            with self._connect() as con:
                for table in (
                    "resolved_users",
                    "friends_cache_v2",
                    "profile_cache",
                    "hub_cache_v2",
                    "friends_cache",
                    "hub_cache",
                ):
                    try:
                        con.execute(f"DELETE FROM {table}")
                    except sqlite3.DatabaseError:
                        pass
        except sqlite3.DatabaseError:
            self._reset_broken_db()
            self._init_db()
