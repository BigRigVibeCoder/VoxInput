"""
WordDatabase — SQLite-backed protected words list for VoxInput spell corrector.

Words in this database are passed through unchanged by the spell corrector.
Loaded into a set at startup for O(1) lookup during dictation.
"""
import logging
import sqlite3
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS words (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    category    TEXT    NOT NULL DEFAULT 'custom',
    added_at    REAL    NOT NULL DEFAULT (unixepoch('now', 'subsec'))
);
CREATE INDEX IF NOT EXISTS idx_words_word ON words(word COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_words_cat  ON words(category);
"""


class WordDatabase:
    """
    Manages the protected-words list.

    All lookups use an in-memory set — zero DB hits during dictation.
    Writes go to SQLite and update the set atomically.
    Thread-safe: write lock guards DB + set updates.
    """

    def __init__(self, db_path: str | Path):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._set: set[str] = set()
        self._load_into_memory()
        logger.info("WordDatabase loaded: %d protected words from %s",
                    len(self._set), self._path)

    # ── Public API ───────────────────────────────────────────────────────────

    def is_protected(self, word: str) -> bool:
        """O(1) in-memory lookup. Called on every word during dictation."""
        return word.lower() in self._set

    def add_word(self, word: str, category: str = "custom") -> bool:
        """Add a word. Returns True if newly added, False if already exists."""
        w = word.strip().lower()
        if not w:
            return False
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO words(word, category) VALUES(?, ?)", (w, category)
                )
                self._conn.commit()
                self._set.add(w)
                logger.debug("WordDB: added '%s' (%s)", w, category)
                return True
            except sqlite3.IntegrityError:
                return False  # already exists

    def remove_word(self, word: str) -> bool:
        """Remove a word. Returns True if removed."""
        w = word.strip().lower()
        with self._lock:
            cur = self._conn.execute("DELETE FROM words WHERE word=? COLLATE NOCASE", (w,))
            self._conn.commit()
            self._set.discard(w)
            return cur.rowcount > 0

    def get_all(self, filter_text: str = "") -> list[tuple]:
        """Return list of (id, word, category, added_at) for UI display."""
        q = filter_text.strip().lower()
        if q:
            return self._conn.execute(
                "SELECT id, word, category, added_at FROM words "
                "WHERE lower(word) LIKE ? OR lower(category) LIKE ? "
                "ORDER BY category, word",
                (f"%{q}%", f"%{q}%")
            ).fetchall()
        return self._conn.execute(
            "SELECT id, word, category, added_at FROM words ORDER BY category, word"
        ).fetchall()

    def count(self) -> int:
        return len(self._set)

    def reload(self):
        """Re-read DB into memory (e.g. after bulk import)."""
        with self._lock:
            self._load_into_memory()
        logger.info("WordDB reloaded: %d words", len(self._set))

    def seed(self, words: list[tuple[str, str]]):
        """
        Bulk-seed the database. words = [(word, category), ...]
        Skips duplicates. Only runs if DB is empty.
        """
        if self.count() > 0:
            return  # already seeded
        logger.info("WordDB: seeding %d initial words…", len(words))
        t0 = time.monotonic()
        with self._lock:
            self._conn.executemany(
                "INSERT OR IGNORE INTO words(word, category) VALUES(?,?)", words
            )
            self._conn.commit()
            self._load_into_memory()
        logger.info("WordDB: seed complete in %.1fms — %d words",
                    (time.monotonic() - t0) * 1000, len(self._set))

    # ── Internal ─────────────────────────────────────────────────────────────

    def _load_into_memory(self):
        rows = self._conn.execute("SELECT word FROM words").fetchall()
        self._set = {r[0].lower() for r in rows}

    def close(self):
        self._conn.close()
