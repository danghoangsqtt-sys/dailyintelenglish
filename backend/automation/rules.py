"""Phase 62 (ENH-044): the pure rules of automatic production -- when the runner may work, which episodes are due and
what step a project needs next. No I/O, so the tests pin them exactly."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

# The production steps the runner makes, in order (the YouTube package is the last: then the video waits for review).
STEPS = ("project", "script", "learning", "audio", "visual_plan", "video", "thumbnail", "youtube")
STEP_LABELS = {
    "project": "Create the project", "script": "Script", "learning": "Learning content", "audio": "Voice audio",
    "visual_plan": "Visual plan", "video": "Render the video", "thumbnail": "Thumbnail", "youtube": "YouTube package",
}
# The step page a person opens to look at (or fix) a step.
STEP_PAGES = {"project": "/channel", "script": "/step2", "learning": "/step3", "audio": "/step4", "visual_plan": "/step5",
              "video": "/step5", "thumbnail": "/step6", "youtube": "/step7"}


def parse_clock(value: str) -> time:
    """'23:00' -> 23:00; raises ValueError for anything else."""
    hours, minutes = value.split(":")
    if len(hours) != 2 or len(minutes) != 2:
        raise ValueError("Use HH:MM")
    return time(int(hours), int(minutes))


def in_window(now: datetime, start: str, end: str) -> bool:
    """Whether `now` is inside the daily window [start, end); a window may run across midnight (23:00-06:00).
    Equal start and end means the whole day."""
    begin, finish, clock = parse_clock(start), parse_clock(end), now.time()
    if begin == finish:
        return True
    if begin < finish:
        return begin <= clock < finish
    return clock >= begin or clock < finish


def window_started(now: datetime, start: str, end: str) -> datetime:
    """When the window that contains `now` began (the night's key: one night = one window)."""
    begin = parse_clock(start)
    started = datetime.combine(now.date(), begin, tzinfo=now.tzinfo)
    if started > now:
        started -= timedelta(days=1)
    return started


def due_episodes(episodes: list[dict[str, Any]], today: date, days_ahead: int) -> list[dict[str, Any]]:
    """Episodes to make: not published, with a publishing date on or before today + `days_ahead` (late ones first),
    whose project is not finished yet. Each episode dict carries `publish_date`, `status` and `finished`."""
    last = today + timedelta(days=days_ahead)
    due = [episode for episode in episodes
           if episode.get("publish_date") and episode.get("status") != "published" and not episode.get("finished")
           and date.fromisoformat(episode["publish_date"]) <= last]
    return sorted(due, key=lambda episode: (episode["publish_date"], episode.get("number") or 0))


def next_step(progress: dict[str, bool] | None, *, has_visual_plan: bool) -> str | None:
    """The first step still to do for a project (None: everything is made). `progress` holds the dashboard's step flags
    (script, learning, audio, video, thumbnail, youtube); a project that does not exist yet needs "project"."""
    if progress is None:
        return "project"
    for step in STEPS[1:]:
        if step == "visual_plan":
            if not progress.get("video") and not has_visual_plan:
                return step
            continue
        if not progress.get(step):
            return step
    return None
