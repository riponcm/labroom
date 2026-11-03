#!/usr/bin/env python3
"""Seed the local Mattermost with the fictional lab: six users, one channel, the chat log.

Creates the users, adds them to the team and the channel, then posts every
message in seed/chat_log.md as the person who wrote it, with the original
date and time prefixed to the text (the Mattermost API ignores create_at).

Credentials: the admin password is read from MM_ADMIN_PASSWORD or asked for on
the terminal without echo. Generated student passwords are written to
.local/mattermost_users.json next to this script's parent folder, which is
git-ignored, so the demo can sign in as any of them. Nothing is printed.

Usage:
    python tools/seed_mattermost.py --team <team-name> [--channel trailnet-lab]
                                    [--url http://localhost:50921] [--admin user]
                                    [--log seed/chat_log.md] [--dry-run]
"""

import argparse
import getpass
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PEOPLE = {
    "Maya Chen": ("maya.chen", "Maya", "Chen"),
    "Priya Nair": ("priya.nair", "Priya", "Nair"),
    "Lucas Moreno": ("lucas.moreno", "Lucas", "Moreno"),
    "Sofia Alvarez": ("sofia.alvarez", "Sofia", "Alvarez"),
    "Omar Haddad": ("omar.haddad", "Omar", "Haddad"),
    "Wei Zhang": ("wei.zhang", "Wei", "Zhang"),
}

LINE = re.compile(r"^\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})\] ([^:]+): (.*)$")


class MM:
    def __init__(self, url):
        self.url = url.rstrip("/")
        self.token = None

    def call(self, method, path, body=None, token=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{self.url}/api/v4{path}", data=data, method=method)
        req.add_header("Content-Type", "application/json")
        tok = token or self.token
        if tok:
            req.add_header("Authorization", f"Bearer {tok}")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                txt = r.read().decode()
                return r.status, (json.loads(txt) if txt else None), r.headers
        except urllib.error.HTTPError as e:
            txt = e.read().decode()
            try:
                return e.code, json.loads(txt), e.headers
            except json.JSONDecodeError:
                return e.code, {"message": txt}, e.headers

    def login(self, login_id, password):
        status, body, headers = self.call("POST", "/users/login", {"login_id": login_id, "password": password})
        if status != 200:
            raise SystemExit(f"login as {login_id} failed: {status} {body.get('message', '')}")
        return headers["Token"], body["id"]


def parse_log(path):
    msgs = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        m = LINE.match(raw.strip())
        if m:
            date, hhmm, name, text = m.groups()
            msgs.append((date, hhmm, name.strip(), text))
    return msgs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:50921")
    ap.add_argument("--admin", default="user", help="admin login id (username or email)")
    ap.add_argument("--team", default=None, help="team name as it appears in the Mattermost URL; default: the admin's first team")
    ap.add_argument("--channel", default="trailnet-lab")
    ap.add_argument("--log", default=str(ROOT / "seed" / "chat_log.md"))
    ap.add_argument("--dry-run", action="store_true", help="parse the log and list what would be created")
    args = ap.parse_args()

    msgs = parse_log(args.log)
    if not msgs:
        raise SystemExit(f"no messages parsed from {args.log}")
    unknown = sorted({n for _, _, n, _ in msgs} - set(PEOPLE))
    if unknown:
        raise SystemExit(f"names in the log without a user mapping: {unknown}")
    if args.dry_run:
        print(f"{len(msgs)} messages, {len(PEOPLE)} users, channel {args.channel}, team {args.team}")
        return 0

    admin_pw = os.environ.get("MM_ADMIN_PASSWORD") or getpass.getpass("Mattermost admin password: ")
    mm = MM(args.url)
    mm.token, admin_id = mm.login(args.admin, admin_pw)

    if args.team:
        status, team, _ = mm.call("GET", f"/teams/name/{args.team}")
        if status != 200:
            raise SystemExit(f"team {args.team!r} not found: {team.get('message', '')}")
    else:
        status, teams, _ = mm.call("GET", f"/users/{admin_id}/teams")
        if status != 200 or not teams:
            raise SystemExit("the admin is in no team; pass --team")
        team = teams[0]
        print(f"using team {team['name']}")
    team_id = team["id"]

    # Users: create or reuse. Passwords kept in a git-ignored file.
    cred_path = ROOT / ".local" / "mattermost_users.json"
    cred_path.parent.mkdir(exist_ok=True)
    creds = json.loads(cred_path.read_text()) if cred_path.exists() else {}
    users = {}
    for display, (username, first, last) in PEOPLE.items():
        status, existing, _ = mm.call("GET", f"/users/username/{username}")
        if status == 200:
            users[display] = existing["id"]
            if username not in creds:
                print(f"user {username} exists but its password is not in {cred_path.name}; posting as admin for them")
        else:
            pw = creds.get(username) or secrets.token_urlsafe(12)
            status, created, _ = mm.call("POST", "/users", {
                "email": f"{username}@example.edu", "username": username, "password": pw,
                "first_name": first, "last_name": last,
            })
            if status not in (200, 201):
                raise SystemExit(f"create user {username} failed: {status} {created.get('message', '')}")
            users[display] = created["id"]
            creds[username] = pw
            print(f"created user {username}")
        mm.call("POST", f"/teams/{team_id}/members", {"team_id": team_id, "user_id": users[display]})
    cred_path.write_text(json.dumps(creds, indent=2))
    try:
        os.chmod(cred_path, 0o600)
    except OSError:
        pass

    # Channel: create or reuse, then add everyone.
    status, chan, _ = mm.call("GET", f"/teams/{team_id}/channels/name/{args.channel}")
    if status != 200:
        status, chan, _ = mm.call("POST", "/channels", {
            "team_id": team_id, "name": args.channel, "display_name": args.channel, "type": "O",
            "purpose": "TrailNet research lab: meetings, papers, progress",
        })
        if status not in (200, 201):
            raise SystemExit(f"create channel failed: {status} {chan.get('message', '')}")
        print(f"created channel {args.channel}")
    channel_id = chan["id"]
    for uid in users.values():
        mm.call("POST", f"/channels/{channel_id}/members", {"user_id": uid})

    # Post the log as each person, in order.
    tokens = {}
    for display, (username, _, _) in PEOPLE.items():
        if username in creds:
            tokens[display], _ = mm.login(username, creds[username])
    posted = 0
    for date, hhmm, name, text in msgs:
        day = datetime.strptime(date, "%Y-%m-%d").strftime("%a %b %d")
        body = {"channel_id": channel_id, "message": f"({day}, {hhmm}) {text}"}
        tok = tokens.get(name)
        if tok is None:
            body["message"] = f"({day}, {hhmm}) [{name}] {text}"
        status, resp, _ = mm.call("POST", "/posts", body, token=tok)
        if status not in (200, 201):
            raise SystemExit(f"post failed after {posted} messages: {status} {resp.get('message', '')}")
        posted += 1
        time.sleep(0.2)
    print(f"posted {posted} messages to {args.channel}")
    print(f"student passwords are in {cred_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
