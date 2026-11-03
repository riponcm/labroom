#!/usr/bin/env python3
"""Actions the organizer agent takes for the PI that Switch agents cannot do themselves.

Switch agents can post in rooms they are in, but cannot pin a post or open a
private chat with a person. These actions run with the PI's delegated account
(in the demo, the fictional maya.chen from the git-ignored .local file; in a
real lab, a personal access token the PI grants). Every action is appended to
out/actions.log so the auditor and the PI can see what was done on her behalf.

Usage:
    python tools/lab_actions.py pin --contains "Group meeting" [--from organizer.lab]
    python tools/lab_actions.py unpin --contains "Group meeting"
    python tools/lab_actions.py dm wei.zhang --file out/dm_2026-11-03_wei.md --request "Dr. Chen asked in DM"
    python tools/lab_actions.py meeting add --title "Group meeting" --start 2026-11-05T10:00 \
        --end 2026-11-05T10:45 --link https://zoom.us/j/... --attendees all [--agenda-file out/agenda.md]
    python tools/lab_actions.py meeting list
Options: --channel (default trailnet), --as (default maya.chen).
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmconf import mattermost_url  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
MEETINGS = OUT / "meetings.json"
LOG = OUT / "actions.log"
STUDENTS = ["priya.nair", "lucas.moreno", "sofia.alvarez", "omar.haddad", "wei.zhang"]


class MM:
    def __init__(self, user):
        self.url = mattermost_url()
        creds = json.loads((ROOT / ".local" / "mattermost_users.json").read_text())
        if user not in creds:
            raise SystemExit(f"no delegated credentials for {user}")
        headers, me = self.call("POST", "/users/login", body={"login_id": user, "password": creds[user]}, auth=False)
        self.token, self.me = headers["Token"], me

    def call(self, method, path, body=None, auth=True):
        req = urllib.request.Request(self.url + "/api/v4" + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None)
        req.add_header("Content-Type", "application/json")
        if auth:
            req.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.headers, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            raise SystemExit(f"{method} {path} failed: {e.code} {e.read().decode()[:200]}")

    def channel(self, name):
        _, teams = self.call("GET", "/users/me/teams")
        _, chan = self.call("GET", f"/teams/{teams[0]['id']}/channels/name/{name}")
        return chan

    def user_id(self, username):
        _, u = self.call("GET", f"/users/username/{username}")
        return u["id"]


def log(action, **fields):
    OUT.mkdir(exist_ok=True)
    entry = {"time": datetime.now().isoformat(timespec="seconds"), "action": action, **fields}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def find_post(mm, channel_id, contains, author, pinned_only=False):
    author_id = mm.user_id(author)
    path = f"/channels/{channel_id}/pinned" if pinned_only else f"/channels/{channel_id}/posts?per_page=100"
    _, posts = mm.call("GET", path)
    if pinned_only:
        posts["order"] = sorted(posts["posts"], key=lambda k: -posts["posts"][k]["create_at"])
    for pid in posts["order"]:
        p = posts["posts"][pid]
        if p["user_id"] == author_id and contains.lower() in p["message"].lower():
            return p
    raise SystemExit(f"no recent post by {author} containing {contains!r}")


def cmd_pin(args, unpin=False):
    mm = MM(args.as_user)
    chan = mm.channel(args.channel)
    post = find_post(mm, chan["id"], args.contains, args.author, pinned_only=unpin)
    mm.call("POST", f"/posts/{post['id']}/{'unpin' if unpin else 'pin'}")
    log("unpin" if unpin else "pin", channel=args.channel, post_id=post["id"], contains=args.contains, by=args.as_user)
    print(f"{'unpinned' if unpin else 'pinned'} post {post['id']} by {args.author}")


def cmd_dm(args):
    text = Path(args.file).read_text(encoding="utf-8").strip() if args.file else args.text
    if not text:
        raise SystemExit("nothing to send: pass --file or --text")
    if args.to not in STUDENTS:
        raise SystemExit(f"{args.to} is not a lab student; private messages go only to students")
    mm = MM(args.as_user)
    _, chan = mm.call("POST", "/channels/direct", body=[mm.me["id"], mm.user_id(args.to)])
    _, post = mm.call("POST", "/posts", body={"channel_id": chan["id"], "message": text})
    log("dm", to=args.to, post_id=post["id"], chars=len(text), request=args.request, by=args.as_user)
    print(f"sent a private message to {args.to} from {args.as_user}")


def load_meetings():
    return json.loads(MEETINGS.read_text(encoding="utf-8")) if MEETINGS.exists() else []


def cmd_meeting_add(args):
    meetings = load_meetings()
    for t in (args.start, args.end):
        datetime.fromisoformat(t)
    mid = f"M{len(meetings) + 1}"
    attendees = STUDENTS if args.attendees == "all" else [a.strip() for a in args.attendees.split(",")]
    meetings.append({
        "id": mid, "title": args.title, "start": args.start, "end": args.end, "link": args.link,
        "attendees": attendees, "agenda_file": args.agenda_file, "channel": args.channel,
        "sent": {"reminder": False, "start": False, "ended": False},
    })
    OUT.mkdir(exist_ok=True)
    MEETINGS.write_text(json.dumps(meetings, indent=2, ensure_ascii=False), encoding="utf-8")
    log("meeting_add", id=mid, title=args.title, start=args.start, end=args.end)
    print(f"registered meeting {mid}: {args.title} {args.start} to {args.end}")


def cmd_meeting_list(args):
    for m in load_meetings():
        print(f"{m['id']}  {m['start']} to {m['end']}  {m['title']}  sent={m['sent']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--channel", default="trailnet")
    ap.add_argument("--as", dest="as_user", default="maya.chen")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("pin", "unpin"):
        p = sub.add_parser(name)
        p.add_argument("--contains", required=True)
        p.add_argument("--from", dest="author", default="organizer.lab")
    p = sub.add_parser("dm")
    p.add_argument("to")
    p.add_argument("--file")
    p.add_argument("--text")
    p.add_argument("--request", default="", help="who asked, and where")
    m = sub.add_parser("meeting")
    msub = m.add_subparsers(dest="mcmd", required=True)
    a = msub.add_parser("add")
    a.add_argument("--title", required=True)
    a.add_argument("--start", required=True, help="local time, e.g. 2026-11-05T10:00")
    a.add_argument("--end", required=True)
    a.add_argument("--link", required=True)
    a.add_argument("--attendees", default="all")
    a.add_argument("--agenda-file")
    msub.add_parser("list")
    args = ap.parse_args()
    if args.cmd == "pin":
        cmd_pin(args)
    elif args.cmd == "unpin":
        cmd_pin(args, unpin=True)
    elif args.cmd == "dm":
        cmd_dm(args)
    elif args.mcmd == "add":
        cmd_meeting_add(args)
    else:
        cmd_meeting_list(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
