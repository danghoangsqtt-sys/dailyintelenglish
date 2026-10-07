"""Async SQLite connection management (aiosqlite)."""

import sqlite3
from datetime import datetime, timezone

import aiosqlite

from app.core.config import settings
from app.core.paths import get_project_root

MIGRATIONS_DIR = get_project_root() / "app" / "db" / "migrations"


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
    cursor = await connection.execute("SELECT filename FROM schema_migrations")
    applied = {row[0] for row in await cursor.fetchall()}
    for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if migration_file.name in applied:
            continue
        script = migration_file.read_text(encoding="utf-8")
        try:
            await connection.executescript(script)
        except sqlite3.OperationalError as exc:
            # A database that predates schema_migrations tracking may already have this
            # migration's effect applied (e.g. an ALTER TABLE ADD COLUMN from before this
            # fix existed) -- record it as applied and continue rather than crashing
            # startup. Any other OperationalError is a real failure and must still raise.
            message = str(exc)
            if "duplicate column name" not in message and "already exists" not in message:
                raise
        await connection.execute(
            "INSERT INTO schema_migrations (filename, applied_at) VALUES (?, ?)",
            (migration_file.name, datetime.now(timezone.utc).isoformat()),
        )
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
