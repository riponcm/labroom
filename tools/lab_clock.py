#!/usr/bin/env python3
"""The lab clock: nudges the organizer at meeting times. Switch has no timer of its own.

Reads out/meetings.json (written by `lab_actions.py meeting add`). For each meeting
it sends the organizer a private "[clock]" message, from the PI's delegated
account, at three moments:

    reminder  REMIND minutes before the start   -> organizer posts a reminder in the room
    start     at the start                      -> organizer posts "starting now"
    ended     FOLLOWUP minutes after the end    -> organizer asks for the transcript

The nudges go to the organizer's direct chat, so the lab room only sees the
organizer's own posts. Run it in a terminal and leave it running:

    python tools/lab_clock.py [--remind 15] [--followup 5] [--every 30] [--once]
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEETINGS = ROOT / "out" / "meetings.json"


def nudge(meeting, kind):
    start = datetime.fromisoformat(meeting["start"])
    minutes = max(0, round((start - datetime.now()).total_seconds() / 60))
    when = f"starts in {minutes} minutes" if kind == "reminder" else f"{meeting['start']} to {meeting['end']}"
    text = f"[clock] {kind} {meeting['id']}: {meeting['title']} ({when})"
    subprocess.run([sys.executable, str(ROOT / "tools" / "post_as.py"), "maya.chen", text, "--dm", "organizer.lab"],
                   check=True)
    print(f"{datetime.now():%H:%M:%S} sent {kind} for {meeting['id']}", flush=True)


def tick(remind, followup):
    if not MEETINGS.exists():
        return
    meetings = json.loads(MEETINGS.read_text(encoding="utf-8"))
    now = datetime.now()
    changed = False
    for m in meetings:
        start, end = datetime.fromisoformat(m["start"]), datetime.fromisoformat(m["end"])
        plan = [("reminder", start - timedelta(minutes=remind)), ("start", start),
                ("ended", end + timedelta(minutes=followup))]
        for kind, due in plan:
            if not m["sent"].get(kind) and now >= due:
                # Skip stale nudges more than an hour late, e.g. after the laptop slept.
                if now - due < timedelta(hours=1):
                    nudge(m, kind)
                m["sent"][kind] = True
                changed = True
    if changed:
        MEETINGS.write_text(json.dumps(meetings, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--remind", type=float, default=15, help="minutes before the start")
    ap.add_argument("--followup", type=float, default=5, help="minutes after the end")
    ap.add_argument("--every", type=float, default=30, help="seconds between checks")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    print(f"lab clock running: reminder {args.remind} min before, follow-up {args.followup} min after", flush=True)
    while True:
        tick(args.remind, args.followup)
        if args.once:
            return 0
        time.sleep(args.every)


if __name__ == "__main__":
    sys.exit(main())
