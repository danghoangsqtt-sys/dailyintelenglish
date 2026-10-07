r"""Task 29.6 (ENH-020): fill the Shot Library with ready-made pictures of the cast, a scene at a time, resumable.

    venv\Scripts\python scripts\build_shot_library.py --base http://127.0.0.1:8000
    venv\Scripts\python scripts\build_shot_library.py --scenes builtin-cafe,builtin-park --max-minutes 120

The app must be running (it owns the GPU queue). For every scene of the plan the script makes a throw-away builder
project with the cast (Lan + Minh by default), lets the normal shot job draw the framing set (a single of each person,
a duo close and a duo wide) and copies every picture that passed its checks into the library as `pending`. Pictures that
still carry a review note are not copied (they are counted). Nothing is approved here: the owner looks at the pictures
once on the Shot Library page, and only approved ones are ever reused.

Resumable: a scene that already holds a full set for this cast in the library is skipped, so after an interruption (or when
`--max-minutes` runs out) the same command carries on. The builder project is deleted at the end; the library keeps its own
copies of the pictures. A coverage report is printed and, with --report, written as Markdown.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

DEFAULT_SCENES = [
    "builtin-cafe", "builtin-classroom", "builtin-library", "builtin-park",
    "builtin-office", "builtin-living-room", "builtin-street", "builtin-kitchen",
]
FRAMING_SET = 4  # a single of each person, a duo close and a duo wide
POLL_SECONDS = 5


def call(base: str, method: str, path: str, body=None):
    request = urllib.request.Request(
        f"{base}{path}", method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            envelope = json.load(response)
    except urllib.error.HTTPError as error:
        raise SystemExit(f"{method} {path} failed: {error.code} {error.read().decode()[:300]}") from None
    return envelope["data"]


def wait_job(base: str, job: dict, say) -> dict:
    last = None
    while True:
        current = call(base, "GET", f"/api/visuals/jobs/{job['id']}")
        stage = f"{current['status']} {current.get('stage') or ''} {current.get('progress')}"
        if stage != last:
            say(f"    {stage}")
            last = stage
        if current["status"] in ("complete", "error", "cancelled"):
            return current
        time.sleep(POLL_SECONDS)


def build(base: str, scene_ids: list[str], names: list[str], max_minutes: float | None, say=print) -> dict:
    characters = {c["name"]: c for c in call(base, "GET", "/api/visuals/characters")}
    missing = [name for name in names if name not in characters or characters[name]["status"] != "locked"]
    if missing:
        raise SystemExit(f"Characters not found or not locked in the library: {', '.join(missing)}")
    cast_ids = [characters[name]["id"] for name in names]
    scenes = {s["id"]: s for s in call(base, "GET", "/api/visuals/scenes")}
    unknown = [scene_id for scene_id in scene_ids if scene_id not in scenes]
    if unknown:
        raise SystemExit(f"Unknown scenes: {', '.join(unknown)}")

    def have(scene_id: str) -> int:
        shots = call(base, "GET", f"/api/visuals/library/shots?scene_id={scene_id}")
        return sum(1 for shot in shots if shot["review_state"] != "rejected" and not shot["stale"]
                   and set(shot["character_ids"]) <= set(cast_ids) and not shot["action"])

    todo = [scene_id for scene_id in scene_ids if have(scene_id) < FRAMING_SET]
    report = {"scenes": {}, "skipped": [s for s in scene_ids if s not in todo], "flagged": 0, "stopped_early": False}
    if not todo:
        say("Every scene of the plan already has its full set in the library.")
        return report
    deadline = time.monotonic() + max_minutes * 60 if max_minutes else None
    project = call(base, "POST", "/api/projects", {
        "name": "[Shot Library Builder]", "topic": "Shot library", "cefr_level": "B1", "duration_minutes": 2,
        "num_speakers": len(names), "genre": "small_talk", "accent": "american",
        "speakers": [{"name": name, "gender": "female" if characters[name]["gender"] == "female" else "male",
                      "accent": "american"} for name in names],
    })
    try:
        call(base, "PUT", f"/api/projects/{project['id']}/visuals/cast",
             [{"speaker_index": index, "character_id": cast_id} for index, cast_id in enumerate(cast_ids)])
        for number, scene_id in enumerate(todo, 1):
            if deadline and time.monotonic() > deadline:
                report["stopped_early"] = True
                say(f"Time budget used: stopping before {scene_id}. Run the same command to carry on.")
                break
            started = time.monotonic()
            say(f"[{number}/{len(todo)}] {scenes[scene_id]['name']} ...")
            call(base, "PUT", f"/api/projects/{project['id']}/visuals/scenes", [scene_id])
            job = wait_job(base, call(base, "POST", f"/api/projects/{project['id']}/visuals/shots"), say)
            if job["status"] != "complete":
                say(f"    job ended as {job['status']}: {job.get('error')}")
                report["scenes"][scene_id] = {"added": 0, "flagged": 0, "error": job.get("error") or job["status"]}
                continue
            added = flagged = 0
            for shot in call(base, "GET", f"/api/projects/{project['id']}/visuals")["shots"]:
                if shot["kind"] == "insert" or shot["status"] != "complete" or shot["source"] == "library":
                    continue
                if shot.get("review_note"):
                    flagged += 1
                    continue
                call(base, "POST", f"/api/projects/{project['id']}/visuals/shots/{shot['id']}/to-library")
                added += 1
            report["scenes"][scene_id] = {"added": added, "flagged": flagged, "seconds": round(time.monotonic() - started)}
            report["flagged"] += flagged
            say(f"    {added} pictures in the library (pending review), {flagged} left out for a check note, "
                f"{round(time.monotonic() - started)} s")
    finally:
        call(base, "DELETE", f"/api/projects/{project['id']}")
    return report


def render_report(report: dict, scene_ids: list[str], names: list[str]) -> str:
    lines = [f"# Shot Library batch report ({datetime.now():%Y-%m-%d %H:%M})", "",
             f"Cast: {' + '.join(names)}. Plan: {len(scene_ids)} scenes, {FRAMING_SET} pictures each.", "",
             "| Scene | Added (pending review) | Left out (check note) | Seconds |", "|---|---|---|---|"]
    for scene_id in scene_ids:
        if scene_id in report["skipped"]:
            lines.append(f"| {scene_id} | already complete | | |")
        elif scene_id in report["scenes"]:
            row = report["scenes"][scene_id]
            lines.append(f"| {scene_id} | {row['added']} | {row['flagged']} | {row.get('seconds', '')} |"
                         + (f" error: {row['error']}" if row.get("error") else ""))
        else:
            lines.append(f"| {scene_id} | not reached | | |")
    lines += ["", "Look at the pictures on the Shot Library page (/shots) and approve the good ones."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--scenes", default=",".join(DEFAULT_SCENES))
    parser.add_argument("--characters", default="Lan,Minh")
    parser.add_argument("--max-minutes", type=float, default=None, help="stop starting new scenes after this long")
    parser.add_argument("--report", default=None, help="write a Markdown report here")
    args = parser.parse_args(argv)
    scene_ids = [item.strip() for item in args.scenes.split(",") if item.strip()]
    names = [item.strip() for item in args.characters.split(",") if item.strip()]
    report = build(args.base.rstrip("/"), scene_ids, names, args.max_minutes)
    text = render_report(report, scene_ids, names)
    print("\n" + text)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
