#!/usr/bin/env python3
"""Give the fictional lab members initials avatars and set the channel header.

Runs as the seeded members themselves (passwords from the git-ignored
.local/mattermost_users.json written by seed_mattermost.py), so no admin
password is needed. Avatars are plain initials on a workstream colour: the
people are fictional, so no faces.

The header names agents without "@": Mattermost posts a system message when
the header changes, and an @-mention in it could wake an agent.

Usage:
    python tools/polish_mattermost.py [--url http://localhost:50521]
                                      [--channel trailnet-lab] [--no-header]
"""

import argparse
import io
import json
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmconf import mattermost_url  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Workstream colours from the validated categorical palette (light mode).
PEOPLE = [
    # username, initials, colour, role line for the profile position field
    ("maya.chen", "MC", "#52514e", "PI"),
    ("priya.nair", "PN", "#2a78d6", "PhD 3, lead: model and quantization"),
    ("lucas.moreno", "LM", "#eb6834", "PhD 1: camera node firmware and power"),
    ("sofia.alvarez", "SA", "#1baf7a", "MS 2: frames, labeling, datasets"),
    ("omar.haddad", "OH", "#6250d6", "MS 1: evaluation and paper"),
    ("wei.zhang", "WZ", "#e34948", "PhD 2: night infrared adaptation"),
]

HEADER = (
    "**TrailNet Lab** · on-device wildlife counting · "
    "Coordinator routes · Scribe: meetings, decisions, tasks · Librarian: papers · "
    "Reporter: lab board · Logbook: daily logs by DM · Auditor: status and risks · "
    "Workshop paper due **Dec 1** · Model budget **250 KB** · Pinned: brief, guide, log format"
)


def avatar_png(initials, colour, size=256):
    img = Image.new("RGB", (size, size), colour)
    draw = ImageDraw.Draw(img)
    font = None
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(name, int(size * 0.42))
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    box = draw.textbbox((0, 0), initials, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.text(((size - w) / 2 - box[0], (size - h) / 2 - box[1]), initials, fill="white", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class MM:
    def __init__(self, url):
        self.url = url.rstrip("/")

    def request(self, method, path, token=None, body=None, raw=None, content_type="application/json"):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(f"{self.url}/api/v4{path}", data=data, method=method)
        req.add_header("Content-Type", content_type)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
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

    def login(self, username, password):
        status, body, headers = self.request("POST", "/users/login", body={"login_id": username, "password": password})
        if status != 200:
            raise SystemExit(f"login as {username} failed: {status} {body.get('message', '')}")
        return headers["Token"], body["id"]

    def upload_image(self, token, user_id, png):
        boundary = uuid.uuid4().hex
        parts = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="image"; filename="avatar.png"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode() + png + f"\r\n--{boundary}--\r\n".encode()
        return self.request("POST", f"/users/{user_id}/image", token=token, raw=parts,
                            content_type=f"multipart/form-data; boundary={boundary}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=None, help="Mattermost URL; default: found with docker port")
    ap.add_argument("--channel", default="trailnet-lab")
    ap.add_argument("--no-header", action="store_true")
    ap.add_argument("--pins", action="store_true", help="post and pin the lab guide, brief, log format and lab board")
    args = ap.parse_args()
    args.url = args.url or mattermost_url()

    cred_path = ROOT / ".local" / "mattermost_users.json"
    if not cred_path.exists():
        raise SystemExit(f"{cred_path} not found; run tools/seed_mattermost.py first")
    creds = json.loads(cred_path.read_text())
    mm = MM(args.url)

    tokens = {}
    for username, initials, colour, position in PEOPLE:
        if username not in creds:
            print(f"skip {username}: no stored password")
            continue
        token, user_id = mm.login(username, creds[username])
        tokens[username] = token
        status, body, _ = mm.upload_image(token, user_id, avatar_png(initials, colour))
        if status not in (200, 201):
            raise SystemExit(f"avatar upload for {username} failed: {status} {body.get('message', '')}")
        mm.request("PUT", f"/users/{user_id}/patch", token=token, body={"position": position})
        print(f"avatar and role set for {username}")

    if not args.no_header and "maya.chen" in tokens:
        token = tokens["maya.chen"]
        status, teams, _ = mm.request("GET", "/users/me/teams", token=token)
        team_id = teams[0]["id"]
        status, chan, _ = mm.request("GET", f"/teams/{team_id}/channels/name/{args.channel}", token=token)
        if status != 200:
            raise SystemExit(f"channel {args.channel} not found: {chan.get('message', '')}")
        status, resp, _ = mm.request("PUT", f"/channels/{chan['id']}/patch", token=token, body={"header": HEADER})
        if status != 200:
            raise SystemExit(f"header update failed: {status} {resp.get('message', '')}")
        print(f"header set on {args.channel} by maya.chen")

    if args.pins and "maya.chen" in tokens:
        pin_guides(mm, tokens["maya.chen"], args.channel)
    return 0


LOG_FORMAT = """📒 **Daily log format** (logbook writes this for you from a direct message)

```
📒 Daily log · Tue Nov 3, 2026 · Priya Nair · model and quantization · 4.0 h
Done
  • Reran the night test on the v0.3 split: day 88.3, night 73.1 · 2.5 h
  • Added per-class recall to the eval CSV · 1.5 h
Evidence: commits 3f2a1c9, 7d0e4b2 · model/results.md
Blockers: none
Next: per-site night breakdown for Wei
```"""


def pin_guides(mm, token, channel):
    """Post the reference material as Maya and pin it. Bookmarks need a paid licence; pins are free.
    None of these posts mention an agent with @, so no agent wakes."""
    status, teams, _ = mm.request("GET", "/users/me/teams", token=token)
    status, chan, _ = mm.request("GET", f"/teams/{teams[0]['id']}/channels/name/{channel}", token=token)
    channel_id = chan["id"]
    status, pinned, _ = mm.request("GET", f"/channels/{channel_id}/pinned", token=token)
    already = {pp["message"].splitlines()[0] for pp in (pinned or {}).get("posts", {}).values() if pp.get("message")}
    brief = (ROOT / "seed" / "project_brief.md").read_text(encoding="utf-8")
    brief = brief.split("```")[1].strip() if "```" in brief else brief
    posts = [
        ("📋 **Project brief**\n\n" + brief, None),
        ((ROOT / "docs" / "LAB_GUIDE.md").read_text(encoding="utf-8"), None),
        (LOG_FORMAT, None),
        ("📊 **Lab board, week of Oct 26.** The reporter posts a new one every Monday.",
         ROOT / "seed" / "board_week_oct26.png"),
    ]
    for text, attach in reversed(posts):
        if text.splitlines()[0] in already:
            print("already pinned:", text.splitlines()[0].encode("ascii", "ignore").decode()[:60])
            continue
        file_ids = []
        if attach is not None:
            boundary = uuid.uuid4().hex
            raw = (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"channel_id\"\r\n\r\n{channel_id}\r\n"
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{attach.name}\"\r\n"
                "Content-Type: image/png\r\n\r\n"
            ).encode() + attach.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
            status, up, _ = mm.request("POST", "/files", token=token, raw=raw,
                                       content_type=f"multipart/form-data; boundary={boundary}")
            file_ids = [f["id"] for f in up["file_infos"]]
        status, post, _ = mm.request("POST", "/posts", token=token,
                                     body={"channel_id": channel_id, "message": text, "file_ids": file_ids})
        if status not in (200, 201):
            raise SystemExit(f"pin post failed: {status} {post.get('message', '')}")
        mm.request("POST", f"/posts/{post['id']}/pin", token=token)
        print("pinned:", text.splitlines()[0].encode("ascii", "ignore").decode().strip()[:60])


if __name__ == "__main__":
    sys.exit(main())
