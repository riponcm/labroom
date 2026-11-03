#!/usr/bin/env python3
"""Print the latest messages in a room (and their thread replies), read as a seeded member.

Usage:
    python tools/tail_room.py [--channel trailnet] [-n 10] [--as maya.chen] [--since-minutes 30]
"""

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmconf import mattermost_url  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="trailnet")
    ap.add_argument("-n", type=int, default=10, help="number of top-level posts")
    ap.add_argument("--as", dest="user", default="maya.chen")
    ap.add_argument("--since-minutes", type=float, default=None)
    ap.add_argument("--width", type=int, default=1200, help="characters per message")
    args = ap.parse_args()
    url = mattermost_url()
    creds = json.loads((ROOT / ".local" / "mattermost_users.json").read_text())

    def call(method, path, token=None, body=None):
        req = urllib.request.Request(url + "/api/v4" + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None)
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.headers, json.loads(r.read() or b"null")

    headers, _ = call("POST", "/users/login", body={"login_id": args.user, "password": creds[args.user]})
    token = headers["Token"]
    _, teams = call("GET", "/users/me/teams", token)
    _, chan = call("GET", f"/teams/{teams[0]['id']}/channels/name/{args.channel}", token)
    _, posts = call("GET", f"/channels/{chan['id']}/posts?per_page=200", token)
    names = {}

    def name(uid):
        if uid not in names:
            _, u = call("GET", f"/users/{uid}", token)
            names[uid] = (f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u["username"])
        return names[uid]

    cutoff = (time.time() - args.since_minutes * 60) * 1000 if args.since_minutes else 0
    items = [posts["posts"][pid] for pid in posts["order"]]
    items = [p for p in items if p["create_at"] >= cutoff and p.get("type", "") == ""]
    roots = [p for p in items if not p.get("root_id")][: args.n]
    out = sys.stdout.buffer
    for root in reversed(roots):
        t = time.strftime("%H:%M", time.localtime(root["create_at"] / 1000))
        out.write(f"\n=== {t} {name(root['user_id'])}: {root['message'][:args.width]}\n".encode("utf-8"))
        replies = sorted((p for p in items if p.get("root_id") == root["id"]), key=lambda p: p["create_at"])
        for r in replies:
            out.write(f"    -> {name(r['user_id'])}: {r['message'][:args.width]}\n".encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
