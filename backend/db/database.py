"""Async SQLite connection management (aiosqlite)."""

import re
import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone

import aiosqlite

from backend.core.config import settings
from backend.core import paths

MIGRATIONS_DIR = paths.MIGRATIONS_DIR


class Database:
    """Singleton holder for the shared aiosqlite connection."""

    _instance: "Database | None" = None

    def __init__(self) -> None:
        self._connection: aiosqlite.Connection | None = None

    @classmethod
    def instance(cls) -> "Database":
        """Return the process-wide Database singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def connect(self) -> aiosqlite.Connection:
        """Open the shared connection if not already open, with foreign keys enforced."""
        if self._connection is None:
            settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
            self._connection = await aiosqlite.connect(settings.db_path)
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    async def close(self) -> None:
        """Close the shared connection if open."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    @property
    def connection(self) -> aiosqlite.Connection:
        """Return the open connection, raising if `connect()` has not run yet."""
        if self._connection is None:
            raise RuntimeError("Database not connected — call init_db() during startup first")
        return self._connection


# (slug, name, place, staging, category); ids are `builtin-<slug>`.
BUILTIN_SCENES = (
    ("classroom", "Classroom", "a sunny classroom with a whiteboard", "standing", "school"),
    ("cafe", "Cafe", "a cozy street cafe", "seated", "city"),
    ("library", "Library", "a bright university library", "standing", "school"),
    ("kitchen", "Kitchen", "a bright home kitchen", "standing", "home"),
    ("park", "Park", "a green city park", "standing", "city"),
    ("office", "Office", "a modern bright office", "seated", "work"),
    # Task 23.3 pack: short on purpose (the plate carries the detail; the place is the
    # prompt's tail and is cut first past 77 CLIP tokens).
    ("living-room", "Living room", "a cozy living room", "seated", "home"),
    ("restaurant", "Restaurant", "a small family restaurant", "seated", "city"),
    ("market", "Market", "a busy outdoor market", "standing", "city"),
    ("campus", "Campus", "a green university campus", "standing", "school"),
    ("meeting-room", "Meeting room", "a bright meeting room", "seated", "work"),
    ("street", "City street", "a busy city street", "standing", "city"),
    ("bus-stop", "Bus stop", "a city bus stop", "standing", "travel"),
    ("station", "Train station", "a train station platform", "standing", "travel"),
    ("countryside", "Countryside", "a countryside path", "standing", "countryside"),
    ("beach", "Beach", "a sunny beach", "standing", "nature"),
    # Task 23.3b (owner 2026-10-05): settings that recur in IELTS and Cambridge listening tests,
    # grouped as the owner asked -- city, school, countryside -- plus IELTS Part 1 travel/work.
    ("cinema", "Cinema", "a cinema lobby", "standing", "city"),
    ("supermarket", "Supermarket", "a supermarket aisle", "standing", "city"),
    ("bookshop", "Bookshop", "a cozy bookshop", "standing", "city"),
    ("museum", "Museum", "a quiet museum gallery", "standing", "city"),
    ("sports-centre", "Sports centre", "a sports centre reception", "standing", "city"),
    ("swimming-pool", "Swimming pool", "an indoor swimming pool", "standing", "city"),
    ("zoo", "Zoo", "a zoo with elephants", "standing", "city"),
    ("community-centre", "Community centre", "a community centre hall", "standing", "city"),
    ("clinic", "Clinic", "a small medical clinic", "seated", "city"),
    ("shopping-mall", "Shopping mall", "a busy shopping mall", "standing", "city"),
    ("post-office", "Post office", "a small post office", "standing", "city"),
    ("botanical-garden", "Botanical garden", "a botanical garden", "standing", "city"),
    ("lecture-hall", "Lecture hall", "a university lecture hall", "seated", "school"),
    ("science-lab", "Science lab", "a school science laboratory", "standing", "school"),
    ("canteen", "School canteen", "a busy school canteen", "seated", "school"),
    ("sports-hall", "Sports hall", "a school sports hall", "standing", "school"),
    ("schoolyard", "Schoolyard", "a sunny schoolyard", "standing", "school"),
    ("computer-room", "Computer room", "a school computer room", "seated", "school"),
    ("tutor-office", "Tutor office", "a small tutor office", "seated", "school"),
    ("common-room", "Common room", "a student lounge with sofas", "seated", "school"),
    ("art-room", "Art room", "a school art room", "standing", "school"),
    ("seminar-room", "Seminar room", "a small seminar room", "seated", "school"),
    ("school-gate", "School gate", "a school gate", "standing", "school"),
    ("farm", "Farm", "a small family farm", "standing", "countryside"),
    ("rice-fields", "Rice fields", "green rice fields", "standing", "countryside"),
    ("village-road", "Village road", "a village road", "standing", "countryside"),
    ("mountain-stream", "Mountain stream", "a clear mountain stream", "standing", "countryside"),
    ("mountain-forest", "Mountain forest", "a misty mountain forest", "standing", "countryside"),
    ("village-market", "Village market", "a rural village market", "standing", "countryside"),
    ("summer-camp", "Summer camp", "a summer camp with tents", "standing", "countryside"),
    ("riverside", "Riverside", "a peaceful riverside", "standing", "countryside"),
    ("farmhouse-kitchen", "Farmhouse kitchen", "a cozy farmhouse kitchen", "seated", "countryside"),
    ("orchard", "Orchard", "a fruit orchard", "standing", "countryside"),
    ("lakeside", "Lakeside", "a quiet lakeside", "standing", "countryside"),
    ("hiking-trail", "Hiking trail", "a mountain hiking trail", "standing", "countryside"),
    ("hotel-reception", "Hotel reception", "a hotel reception desk", "standing", "travel"),
    ("travel-agency", "Travel agency", "a small travel agency", "seated", "travel"),
    ("airport", "Airport", "an airport check-in hall", "standing", "travel"),
    ("letting-agency", "Letting agency", "a letting agency office", "seated", "work"),
)
# Task 23.3b: built-ins whose category the owner's grouping changed; a row still on its
# previously seeded category moves, a row the user re-categorised is left alone.
# Task 23.3b plate review: four first-run places drew the wrong thing (a zoo without animals, a
# bedroom for "common room", an RV for "summer camp", a European village). A row still holding
# the old text gets the new one and loses its stale plate; a user-edited place is kept.
PREVIOUS_BUILTIN_PLACES = {
    "zoo": "a city zoo", "common-room": "a student common room",
    "summer-camp": "a summer camp", "village-road": "a quiet village road",
}
PREVIOUS_BUILTIN_CATEGORIES = {
    "cafe": "food", "restaurant": "food", "market": "food", "park": "nature", "countryside": "nature",
}




def _migration_statements(script: str) -> list[str]:
    """Split complete SQLite statements, retaining trigger bodies and quoted semicolons."""
    statements: list[str] = []
    pending = ""
    for character in script:
        pending += character
        if character == ";" and sqlite3.complete_statement(pending):
            statements.append(pending)
            pending = ""
    if _statement_sql(pending).strip():
        if not sqlite3.complete_statement(pending + ";"):
            raise sqlite3.OperationalError("Incomplete migration statement")
        statements.append(pending)
    return statements


def _statement_sql(statement: str) -> str:
    """Remove only leading comments for safe statement classification, without changing SQL strings."""
    return re.sub(r"\A(?:\s|--[^\n]*(?:\n|$)|/\*.*?\*/)*", "", statement, flags=re.DOTALL).strip()


async def _legacy_duplicate_column(
    connection: aiosqlite.Connection, statement: str, filename: str, error: sqlite3.OperationalError,
) -> bool:
    """Resume untracked pre027 additive migrations one statement at a time, never swallow a whole file."""
    if filename >= "027" or "duplicate column name" not in str(error).lower():
        return False
    match = re.fullmatch(r'ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)\s+.+?;?',
                         _statement_sql(statement), flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return False
    table, column = match.groups()
    cursor = await connection.execute(f'PRAGMA table_info("{table}")')
    return any(row["name"] == column for row in await cursor.fetchall())


def migration_functions() -> list[tuple[str, int, Callable]]:
    """SQL functions that data migrations call (040 strips retired emotion tags in Python).

    Every runner registers them before replaying migrations: the app's `_apply_migration`
    and the tests' raw `executescript` replays alike, or 040 fails with "no such function".
    """
    from backend.ai.tts.vocal_cues import caption_text
    from backend.db.edge_only_restore import edge_voice_id, plain_config

    return [
        ("retired_cue_text", 1, caption_text),
        ("edge_plain_config", 1, plain_config),
        ("edge_restored_voice", 3, edge_voice_id),
    ]


async def register_migration_functions(connection: aiosqlite.Connection) -> None:
    for name, arg_count, function in migration_functions():
        await connection.create_function(name, arg_count, function, deterministic=True)


async def _apply_migration(connection: aiosqlite.Connection, filename: str, script: str) -> None:
    """Commit a migration and its tracking record together, or leave neither schema nor record behind."""
    statements = _migration_statements(script)
    await register_migration_functions(connection)
    await connection.execute("BEGIN IMMEDIATE")
    try:
        for statement in statements:
            sql = _statement_sql(statement)
            if not sql:
                continue
            # Historical018 owns BEGIN/COMMIT in its file. The runner now owns that transaction and tracking together.
            if re.fullmatch(r"(?:BEGIN(?:\s+(?:DEFERRED|IMMEDIATE|EXCLUSIVE))?(?:\s+TRANSACTION)?|COMMIT|END)\s*;?",
                            sql, flags=re.IGNORECASE):
                continue
            if re.match(r"(?:ROLLBACK|SAVEPOINT|RELEASE|ATTACH|DETACH|VACUUM|PRAGMA)\b", sql, flags=re.IGNORECASE):
                raise sqlite3.OperationalError("Migration must not alter the runner's transaction or connection")
            try:
                await connection.execute(statement)
            except sqlite3.OperationalError as exc:
                if not await _legacy_duplicate_column(connection, statement, filename, exc):
                    raise
        await connection.execute("INSERT INTO schema_migrations (filename, applied_at) VALUES (?, ?)",
                                 (filename, datetime.now(timezone.utc).isoformat()))
        await connection.commit()
    except BaseException:
        await connection.rollback()
        raise


async def init_db() -> None:
    """Open the database connection and apply each migration file exactly once, in
    filename order, tracked in `schema_migrations`.

    Previously this replayed every migration file on every startup — harmless for
    migrations that only use `CREATE TABLE/INDEX IF NOT EXISTS`, but a real,
    reproducible `sqlite3.OperationalError: duplicate column name` crash on any second
    real app restart once a migration uses `ALTER TABLE ADD COLUMN` (SQLite has no
    `ADD COLUMN IF NOT EXISTS`) — found for real 2026-09-14 while adding migration 005.
    """
    db = Database.instance()
    connection = await db.connect()
    await connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    await connection.commit()
    cursor = await connection.execute("SELECT filename FROM schema_migrations")
    applied = {row[0] for row in await cursor.fetchall()}
    for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if migration_file.name in applied:
            continue
        script = migration_file.read_text(encoding="utf-8")
        await _apply_migration(connection, migration_file.name, script)
    now = datetime.now(timezone.utc).isoformat()
    for slug, name, place, staging, category in BUILTIN_SCENES:
        await connection.execute(
            "INSERT OR IGNORE INTO scenes "
            "(id, name, place, staging, is_builtin, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
            (f"builtin-{slug}", name, place, staging, now, now),
        )
        # Task 23.2: a built-in still on the migration default gets its category.
        await connection.execute(
            "UPDATE scenes SET category = ? WHERE id = ? AND category IN ('other', ?)",
            (category, f"builtin-{slug}", PREVIOUS_BUILTIN_CATEGORIES.get(slug, "other")),
        )
        if slug in PREVIOUS_BUILTIN_PLACES:
            await connection.execute(
                "UPDATE scenes SET place = ?, preview_path = NULL, updated_at = ? WHERE id = ? AND place = ?",
                (place, now, f"builtin-{slug}", PREVIOUS_BUILTIN_PLACES[slug]),
            )
    # Task 23.2: every scene has a reproducible plate seed.
    await connection.execute(
        "UPDATE scenes SET seed = (abs(random()) % 2147483646) + 1 WHERE seed IS NULL"
    )
    await connection.commit()


async def close_db() -> None:
    """Close the shared database connection during shutdown."""
    await Database.instance().close()


async def get_db() -> aiosqlite.Connection:
    """FastAPI dependency yielding the shared aiosqlite connection."""
    return Database.instance().connection
