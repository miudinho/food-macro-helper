"""
Warstwa persystencji (SQLite) dla Macro Day Tracker.

Założenia:
- Baza leży w DATA_DIR (domyślnie /app/data), który jest montowany jako wolumen
  Dockera -> dane przeżywają zatrzymanie / usunięcie kontenera (--rm).
- Wszystkie zapytania są parametryzowane (brak SQL injection).
- Każda operacja otwiera krótkie połączenie (bezpieczne dla wątków Streamlita).
- Tryb WAL + busy_timeout -> brak "database is locked" przy kilku sesjach.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

DATA_DIR = os.environ.get("MACRO_DATA_DIR", "/app/data")
DB_PATH = os.environ.get("MACRO_DB_PATH", os.path.join(DATA_DIR, "macro.db"))

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_state (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    payload     TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at     TEXT    NOT NULL,
    note           TEXT,
    day_mode       TEXT    NOT NULL,
    current_carbs  INTEGER NOT NULL,
    target_carbs   INTEGER NOT NULL,
    target_kcal    INTEGER NOT NULL,
    target_protein INTEGER NOT NULL,
    target_fat     INTEGER NOT NULL,
    kcal           REAL    NOT NULL,
    protein        REAL    NOT NULL,
    fat            REAL    NOT NULL,
    sat_fat        REAL    NOT NULL,
    unsat_fat      REAL    NOT NULL,
    carbs          REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshot_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id  INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    product      TEXT    NOT NULL,
    grams        INTEGER NOT NULL CHECK (grams >= 0),
    kcal         REAL    NOT NULL,
    protein      REAL    NOT NULL,
    fat          REAL    NOT NULL,
    sat_fat      REAL    NOT NULL,
    unsat_fat    REAL    NOT NULL,
    carbs        REAL    NOT NULL,
    position     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_items_snapshot ON snapshot_items(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_created ON snapshots(created_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Tworzy schemat (idempotentnie) i ustawia WAL."""
    with _connect() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.executescript(SCHEMA_SQL)
        ver = conn.execute("PRAGMA user_version").fetchone()[0]
        if ver < SCHEMA_VERSION:
            # Miejsce na przyszłe migracje (ALTER TABLE ...)
            conn.execute(f"PRAGMA user_version = {int(SCHEMA_VERSION)}")
    # Plik bazy tylko dla właściciela procesu
    try:
        os.chmod(DB_PATH, 0o600)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Bieżący stan (autozapis) – "ostatnie wpisy" przywracane po restarcie
# ---------------------------------------------------------------------------
def save_state(state: dict[str, Any]) -> None:
    payload = json.dumps(state, ensure_ascii=False)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO app_state (id, payload, updated_at) VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET payload = excluded.payload,
                                          updated_at = excluded.updated_at
            """,
            (payload, _now()),
        )


def load_state() -> tuple[dict[str, Any], str | None]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT payload, updated_at FROM app_state WHERE id = 1"
        ).fetchone()
    if not row:
        return {}, None
    try:
        return json.loads(row["payload"]), row["updated_at"]
    except (json.JSONDecodeError, TypeError):
        return {}, None


# ---------------------------------------------------------------------------
# Zapisy (snapshoty) – tworzone przyciskiem "Zapisz"
# ---------------------------------------------------------------------------
def save_snapshot(
    *,
    note: str | None,
    day_mode: str,
    current_carbs: int,
    target_carbs: int,
    target: dict[str, int],
    totals: dict[str, float],
    items: list[dict[str, Any]],
) -> int:
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            cur = conn.execute(
                """
                INSERT INTO snapshots (created_at, note, day_mode, current_carbs,
                    target_carbs, target_kcal, target_protein, target_fat,
                    kcal, protein, fat, sat_fat, unsat_fat, carbs)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _now(),
                    (note or "").strip()[:200] or None,
                    day_mode,
                    int(current_carbs),
                    int(target_carbs),
                    int(target["kcal"]),
                    int(target["protein"]),
                    int(target["fat"]),
                    float(totals["kcal"]),
                    float(totals["protein"]),
                    float(totals["fat"]),
                    float(totals["sat_fat"]),
                    float(totals["unsat_fat"]),
                    float(totals["carbs"]),
                ),
            )
            snap_id = cur.lastrowid
            conn.executemany(
                """
                INSERT INTO snapshot_items (snapshot_id, product, grams, kcal,
                    protein, fat, sat_fat, unsat_fat, carbs, position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        snap_id,
                        it["product"],
                        int(it["grams"]),
                        float(it["kcal"]),
                        float(it["protein"]),
                        float(it["fat"]),
                        float(it["sat_fat"]),
                        float(it["unsat_fat"]),
                        float(it["carbs"]),
                        pos,
                    )
                    for pos, it in enumerate(items)
                ],
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    return int(snap_id)


def list_snapshots(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT s.*, (SELECT COUNT(*) FROM snapshot_items i
                         WHERE i.snapshot_id = s.id) AS items_count
            FROM snapshots s ORDER BY s.id DESC LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [dict(r) for r in rows]


def get_snapshot(snapshot_id: int) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    with _connect() as conn:
        snap = conn.execute(
            "SELECT * FROM snapshots WHERE id = ?", (int(snapshot_id),)
        ).fetchone()
        items = conn.execute(
            "SELECT * FROM snapshot_items WHERE snapshot_id = ? ORDER BY position",
            (int(snapshot_id),),
        ).fetchall()
    return (dict(snap) if snap else None), [dict(i) for i in items]


def delete_snapshot(snapshot_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM snapshots WHERE id = ?", (int(snapshot_id),))
