import sqlite3
from storage.paths import get_cache_path


class CacheStore:
    def __init__(self):
        self.path = get_cache_path()
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.path) as con:
            con.execute("CREATE TABLE IF NOT EXISTS resolved_users (input TEXT PRIMARY KEY, user_id INTEGER, updated_at INTEGER)")

    def clear_cache(self):
        with sqlite3.connect(self.path) as con:
            con.execute("DELETE FROM resolved_users")
