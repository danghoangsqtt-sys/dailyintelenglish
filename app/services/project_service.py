"""Project CRUD and state-machine logic. Full CRUD lands in Phase 1 Task 1.2."""

import aiosqlite


async def list_projects(db: aiosqlite.Connection) -> list[dict]:
    """List all projects ordered by most recently updated.

    Args:
        db: Open aiosqlite connection.

    Returns:
        List of project rows as dicts (empty list if none exist yet).
    """
    cursor = await db.execute(
        "SELECT id, name, status, cefr_level, genre, accent, created_at, updated_at "
        "FROM projects ORDER BY updated_at DESC"
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
