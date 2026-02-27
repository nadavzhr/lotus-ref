"""
NetlistDatabase — in-memory SQLite store for (template, net) pairs.

Extracted from :class:`NetlistQueryService` to separate the database
lifecycle and querying logic from netlist-level semantics (canonical
names, bus expansion, alias resolution, etc.).
"""
from __future__ import annotations

import re
import sqlite3
from threading import RLock

SQLITE_MAX_VARS_PER_QUERY = 900


class NetlistDatabase:
    """In-memory SQLite store for (template, net) pairs.

    Provides regex, exact, and batch-exact (bus-expanded) lookups.
    Thread-safe — all queries are serialised through an internal lock.
    """

    def __init__(self, all_nets_in_templates: dict[str, set[str]]) -> None:
        self._db_lock = RLock()
        self._is_closed = False

        self._db_conn = sqlite3.connect(":memory:", check_same_thread=False)

        # Register a user-defined REGEXP function for SQLite
        def _regexp(expr: str, item: str | None) -> int:
            if item is None:
                return 0
            try:
                return 1 if re.search(expr, item, re.IGNORECASE) else 0
            except re.error:
                # Let the caller handle invalid patterns via pre-validation;
                # inside the SQLite callback we cannot raise, so return 0.
                return 0

        self._db_conn.create_function("REGEXP", 2, _regexp)

        cursor = self._db_conn.cursor()

        # Performance pragmas for bulk insert
        cursor.execute("PRAGMA synchronous = OFF")
        cursor.execute("PRAGMA journal_mode = OFF")
        cursor.execute("PRAGMA cache_size = 100000")
        cursor.execute("PRAGMA temp_store = MEMORY")

        cursor.execute("""
            CREATE TABLE nets (
                template_name TEXT NOT NULL,
                net_name TEXT NOT NULL,
                PRIMARY KEY (template_name, net_name)
            ) WITHOUT ROWID
        """)

        nets_data = [
            (template, net)
            for template, nets in all_nets_in_templates.items()
            for net in nets
        ]
        cursor.executemany(
            "INSERT INTO nets (template_name, net_name) VALUES (?, ?)",
            nets_data,
        )

        self._db_conn.commit()
        cursor.execute("PRAGMA synchronous = NORMAL")

    # ------------------------------------------------------------------
    # Query methods — return raw (template_name, net_name) rows
    # ------------------------------------------------------------------

    def match_regex(self, templates: list[str], pattern: str) -> list[tuple[str, str]]:
        """Return (template, net) rows where *net* matches the regex *pattern*.

        Raises ``re.error`` eagerly if *pattern* is not a valid regex.
        """
        if not templates:
            return []
        # Pre-validate so callers get a clear error instead of silent empty results.
        re.compile(pattern)
        placeholders = ",".join("?" * len(templates))
        return self._execute(
            f"SELECT template_name, net_name FROM nets "
            f"WHERE template_name IN ({placeholders}) AND net_name REGEXP ?",
            (*templates, pattern),
        )

    def match_exact(self, templates: list[str], name: str) -> list[tuple[str, str]]:
        """Return (template, net) rows where *net* equals *name* exactly."""
        if not templates:
            return []
        placeholders = ",".join("?" * len(templates))
        return self._execute(
            f"SELECT template_name, net_name FROM nets "
            f"WHERE template_name IN ({placeholders}) AND net_name = ?",
            (*templates, name),
        )

    def match_bus(self, templates: list[str], expanded: list[str]) -> list[tuple[str, str]]:
        """Return (template, net) rows where *net* is in the *expanded* list.

        Automatically chunks the query to stay within SQLite's variable
        limit.
        """
        if not templates or not expanded:
            return []
        t_placeholders = ",".join("?" * len(templates))
        available_for_nets = max(1, SQLITE_MAX_VARS_PER_QUERY - len(templates))
        results: list[tuple[str, str]] = []
        for start in range(0, len(expanded), available_for_nets):
            chunk = expanded[start : start + available_for_nets]
            n_placeholders = ",".join("?" * len(chunk))
            results.extend(
                self._execute(
                    f"SELECT template_name, net_name FROM nets "
                    f"WHERE template_name IN ({t_placeholders}) "
                    f"AND net_name IN ({n_placeholders})",
                    (*templates, *chunk),
                )
            )
        return results

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Explicitly release the database connection."""
        with self._db_lock:
            if self._is_closed:
                return
            try:
                self._db_conn.close()
            except Exception:
                pass
            finally:
                self._is_closed = True

    def __enter__(self) -> "NetlistDatabase":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        if hasattr(self, "_db_lock"):
            self.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _execute(self, query: str, params: tuple = ()) -> list:
        if self._is_closed:
            raise RuntimeError("NetlistDatabase is closed")
        with self._db_lock:
            cursor = self._db_conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
