#!/usr/bin/env python3
"""Post a message, optionally with a file attached, as one of the seeded lab members.

Used to script demo moments such as "Maya asks for last week's progress" so
they are identical on every take.

Known issue (Nov 3): a post with --file uploaded through this script shows in
Mattermost but never reaches Switch, so the agent never sees it. Plain text posts
from the same account do reach agents, and a file attached with the paperclip in
the chat UI does too. For transcripts, attach in the UI. Passwords come from the git-ignored
.local/mattermost_users.json written by seed_mattermost.py.

Usage:
    python tools/post_as.py priya.nair "@scribe process this transcript" --file seed/transcript_1.txt
    python tools/post_as.py maya.chen "Show me last week's progress." [--channel trailnet-lab]
"""

import argparse
import json
import mimetypes
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def request(url, method, path, token=None, body=None, raw=None, content_type="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(f"{url}/api/v4{path}", data=data, method=method)
    req.add_header("Content-Type", content_type)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else None), r.headers
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        try:
            return e.code, json.loads(txt), e.headers
        except json.JSONDecodeError:
            return e.code, {"message": txt}, e.headers


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("user", help="seeded username, e.g. priya.nair")
    ap.add_argument("message", help="message text; include @agent to address one")
    ap.add_argument("--file", help="file to attach")
    ap.add_argument("--channel", default="trailnet-lab")
    ap.add_argument("--url", default="http://localhost:50521")
    args = ap.parse_args()
    url = args.url.rstrip("/")

    creds = json.loads((ROOT / ".local" / "mattermost_users.json").read_text())
    if args.user not in creds:
        raise SystemExit(f"no stored password for {args.user}")
    status, body, headers = request(url, "POST", "/users/login", body={"login_id": args.user, "password": creds[args.user]})
    if status != 200:
        raise SystemExit(f"login failed: {status} {body.get('message', '')}")
    token = headers["Token"]

    status, teams, _ = request(url, "GET", "/users/me/teams", token=token)
    status, chan, _ = request(url, "GET", f"/teams/{teams[0]['id']}/channels/name/{args.channel}", token=token)
    if status != 200:
        raise SystemExit(f"channel {args.channel} not found: {chan.get('message', '')}")
    channel_id = chan["id"]

    file_ids = []
    if args.file:
        path = Path(args.file)
        mimetype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        boundary = uuid.uuid4().hex
        raw = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"channel_id\"\r\n\r\n{channel_id}\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: {mimetype}\r\n\r\n"
        ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        status, up, _ = request(url, "POST", "/files", token=token, raw=raw,
                                content_type=f"multipart/form-data; boundary={boundary}")
        if status not in (200, 201):
            raise SystemExit(f"upload failed: {status} {up.get('message', '')}")
        file_ids = [f["id"] for f in up["file_infos"]]

    status, post, _ = request(url, "POST", "/posts", token=token,
                              body={"channel_id": channel_id, "message": args.message, "file_ids": file_ids})
    if status not in (200, 201):
        raise SystemExit(f"post failed: {status} {post.get('message', '')}")
    print(f"posted as {args.user} to {args.channel}" + (f" with {Path(args.file).name}" if args.file else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
