"""Find the local Mattermost URL. The port changes every time Switch Console restarts the server."""

import os
import subprocess

CONTAINER = "switchdash-local-mattermost-mattermost-1"


def mattermost_url():
    if os.environ.get("MM_URL"):
        return os.environ["MM_URL"].rstrip("/")
    try:
        out = subprocess.run(["docker", "port", CONTAINER, "8065"], capture_output=True, text=True, timeout=15)
        line = out.stdout.strip().splitlines()[0]
        host, port = line.rsplit(":", 1)
        host = "localhost" if host in ("0.0.0.0", "127.0.0.1", "[::]") else host
        return f"http://{host}:{port}"
    except Exception:
        return "http://localhost:50521"
