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

CREATE TABLE IF NOT EXISTS compound_corrections (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    misheard  TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    correct   TEXT    NOT NULL,
    added_at  REAL    NOT NULL DEFAULT (unixepoch('now', 'subsec'))
);
CREATE INDEX IF NOT EXISTS idx_cc_misheard ON compound_corrections(misheard COLLATE NOCASE);
"""

# Default compound corrections for common ASR misrecognitions.
# Seeded on first run. Users can add more via the database.
_DEFAULT_COMPOUNDS = [
    # Infrastructure
    ("cooper netty's", "kubernetes"),
    ("cooper nettie's", "kubernetes"),
    ("cooper neediest", "kubernetes"),
    ("cooper eighties", "kubernetes"),  # discovered from Paragraph F recording
    ("cube control", "kubectl"),
    ("and simple", "Ansible"),
    ("and symbol", "Ansible"),          # discovered from Paragraph F recording
    ("engine next", "nginx"),
    ("engine x", "nginx"),
    ("pie torch", "PyTorch"),
    ("tensor flow", "TensorFlow"),
    ("pincer flow", "TensorFlow"),    # discovered from Paragraph F recording
    ("tail scale", "Tailscale"),
    ("terra form", "Terraform"),
    ("read is", "Redis"),
    ("rough fauna", "Grafana"),        # discovered from Paragraph F recording
    ("post gress", "Postgres"),
    ("graph queue l", "GraphQL"),
    ("graph q l", "GraphQL"),
    ("type script", "TypeScript"),
    ("java script", "JavaScript"),
    ("next j s", "Next.js"),
    ("ex tool", "xdotool"),
    ("sim spell", "SymSpell"),
    ("pi input", "pynput"),
    ("vox input", "VoxInput"),
    ("hive mind", "HiveMind"),
    ("hi mind", "HiveMind"),            # discovered from live PTT testing
    ("have my", "HiveMind"),            # discovered from live PTT testing
    ("oh droid", "ODROID"),
    ("lie dar", "LIDAR"),
    ("li dar", "LIDAR"),
    # Common API/tech acronyms
    ("a p i", "API"),
    ("a pr", "API"),
    ("a p r", "API"),
    ("see i", "CI"),
    ("see d", "CD"),
]


class WordDatabase:
    """
    Manages the protected-words list.

    All lookups use an in-memory dict — zero DB hits during dictation.
    Maps lowercase word -> original case word.
    Writes go to SQLite and update the dict atomically.
    Thread-safe: write lock guards DB + dict updates.
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
        self._dict: dict[str, str] = {}
        self._compounds: dict[tuple[str, ...], str] = {}
        self._load_into_memory()
        self._seed_compounds()
        logger.info("WordDatabase loaded: %d protected words, %d compound corrections from %s",
                    len(self._dict), len(self._compounds), self._path)

    # ── Public API ───────────────────────────────────────────────────────────

    def get_original_case(self, word: str) -> str | None:
        """O(1) in-memory lookup. Returns True-cased word if protected, else None."""
        return self._dict.get(word.lower())

    def is_protected(self, word: str) -> bool:
        """Legacy helper for UI."""
        return word.lower() in self._dict

    def add_word(self, word: str, category: str = "custom") -> bool:
        """Add a word. Returns True if newly added, False if already exists."""
        w_strip = word.strip()
        w_lower = w_strip.lower()
        if not w_strip:
            return False
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO words(word, category) VALUES(?, ?)", (w_strip, category)
                )
                self._conn.commit()
                self._dict[w_lower] = w_strip
                logger.debug("WordDB: added '%s' (%s)", w_strip, category)
                return True
            except sqlite3.IntegrityError:
                return False  # already exists

    def remove_word(self, word: str) -> bool:
        """Remove a word. Returns True if removed."""
        w = word.strip().lower()
        with self._lock:
            cur = self._conn.execute("DELETE FROM words WHERE word=? COLLATE NOCASE", (w,))
            self._conn.commit()
            self._dict.pop(w, None)
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
        return len(self._dict)

    def reload(self):
        """Re-read DB into memory (e.g. after bulk import)."""
        with self._lock:
            self._load_into_memory()
        logger.info("WordDB reloaded: %d words", len(self._dict))

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
                    (time.monotonic() - t0) * 1000, len(self._dict))

    # ── Internal ─────────────────────────────────────────────────────────────

    def _load_into_memory(self):
        rows = self._conn.execute("SELECT word FROM words").fetchall()
        self._dict = {r[0].lower(): r[0] for r in rows}
        # Load compound corrections into tuple-keyed dict
        cc_rows = self._conn.execute(
            "SELECT misheard, correct FROM compound_corrections"
        ).fetchall()
        self._compounds = {
            tuple(r[0].lower().split()): r[1] for r in cc_rows
        }

    def reload(self):
        """Re-read dictionary and compounds from database (hot-reload)."""
        with self._lock:
            self._load_into_memory()
            logger.info(
                f"WordDB reloaded: {len(self._dict)} words, "
                f"{len(self._compounds)} compound corrections"
            )

    def _seed_compounds(self):
        """Auto-seed default compound corrections on first run."""
        existing = self._conn.execute(
            "SELECT COUNT(*) FROM compound_corrections"
        ).fetchone()[0]
        if existing > 0:
            return
        logger.info("WordDB: seeding %d default compound corrections", len(_DEFAULT_COMPOUNDS))
        with self._lock:
            self._conn.executemany(
                "INSERT OR IGNORE INTO compound_corrections(misheard, correct) VALUES(?,?)",
                _DEFAULT_COMPOUNDS,
            )
            self._conn.commit()
            self._load_into_memory()

    # ── Compound Corrections API ─────────────────────────────────────────────

    def get_compound_corrections(self) -> dict[tuple[str, ...], str]:
        """Return the in-memory compound corrections map (tuple key → correct word)."""
        return self._compounds

    def add_compound_correction(self, misheard: str, correct: str) -> bool:
        """Add a compound correction. Returns True if newly added."""
        m = misheard.strip().lower()
        c = correct.strip()
        if not m or not c:
            return False
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO compound_corrections(misheard, correct) VALUES(?, ?)",
                    (m, c),
                )
                self._conn.commit()
                self._compounds[tuple(m.split())] = c
                logger.debug("WordDB: added compound '%s' → '%s'", m, c)
                return True
            except sqlite3.IntegrityError:
                return False

    def remove_compound_correction(self, misheard: str) -> bool:
        """Remove a compound correction. Returns True if removed."""
        m = misheard.strip().lower()
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM compound_corrections WHERE misheard=? COLLATE NOCASE", (m,)
            )
            self._conn.commit()
            self._compounds.pop(tuple(m.split()), None)
            return cur.rowcount > 0

    def get_all_compounds(self, filter_text: str = "") -> list[tuple]:
        """Return list of (id, misheard, correct, added_at) for UI display."""
        q = filter_text.strip().lower()
        if q:
            return self._conn.execute(
                "SELECT id, misheard, correct, added_at FROM compound_corrections "
                "WHERE lower(misheard) LIKE ? OR lower(correct) LIKE ? "
                "ORDER BY misheard",
                (f"%{q}%", f"%{q}%"),
            ).fetchall()
        return self._conn.execute(
            "SELECT id, misheard, correct, added_at FROM compound_corrections ORDER BY misheard"
        ).fetchall()

    def close(self):
        self._conn.close()
