#!/usr/bin/env python3
"""Render the weekly TrailNet lab board: one image a professor can read in a minute.

Input JSON (written by the reporter agent):
{
  "period": "Oct 26 to Oct 30, 2026",
  "as_of": "2026-11-02",
  "deadline": {"name": "Workshop paper", "date": "2026-12-01"},
  "status": {"label": "at risk", "reason": "camera modules late; night accuracy 73"},
  "people": [
    {"name": "Priya Nair", "workstream": "model", "hours": 18.5, "commits": 5,
     "tasks_done": 3, "tasks_open": 1, "note": ""}
  ],
  "highlights": ["Model at 240 KB, under the 250 KB budget"],
  "blockers": [{"who": "Lucas Moreno", "what": "IR-cut modules late", "since": "2026-10-28"}],
  "waiting": [{"what": "Move Lucas's Fri benchmark deadline", "since": "2026-10-28"}]
}
"hours" may be null when nobody logged hours. "status", "highlights", "blockers"
and "waiting" are optional.

Usage:
    python tools/lab_board.py board.json --out board.png
"""

import argparse
import json
import sys
import textwrap
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e4e3df"
STATUS = {"on track": "#008300", "at risk": "#c98500", "off track": "#e34948"}

# One colour per person, the same as their Mattermost avatar.
PERSON_COLOUR = {
    "Priya Nair": "#2a78d6",
    "Lucas Moreno": "#eb6834",
    "Sofia Alvarez": "#1baf7a",
    "Omar Haddad": "#6250d6",
    "Wei Zhang": "#e34948",
    "Maya Chen": "#52514e",
}


def colour(name):
    return PERSON_COLOUR.get(name, MUTED)


def bar_panel(ax, people, key, title, unit):
    names = [p["name"] for p in people]
    values = [p.get(key) for p in people]
    ys = list(range(len(people)))[::-1]
    vmax = max([v for v in values if isinstance(v, (int, float))] + [1])
    for y, p, v in zip(ys, people, values):
        if isinstance(v, (int, float)) and v > 0:
            ax.barh(y, v, height=0.55, color=colour(p["name"]), zorder=3)
            label = f"{v:g} {unit}"
        else:
            label = "not logged" if v is None else f"0 {unit}"
        note = p.get("note") or ""
        text = label + (f"  ·  {note}" if note and key == "hours" else "")
        ax.text((v if isinstance(v, (int, float)) else 0) + vmax * 0.02, y, text,
                va="center", ha="left", fontsize=8.5, color=TEXT_2)
    ax.set_yticks(ys, names, fontsize=9, color=TEXT)
    ax.set_xlim(0, vmax * 1.9)
    ax.xaxis.set_visible(False)
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.tick_params(axis="y", length=0)
    ax.set_title(title, loc="left", fontsize=10.5, color=TEXT, pad=6)


def list_panel(ax, title, lines, empty):
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=10.5, color=TEXT, pad=6)
    if not lines:
        lines = [empty]
    y = 0.96
    for line in lines:
        wrapped = textwrap.wrap(line, 58) or [""]
        for i, w in enumerate(wrapped):
            ax.text(0.0, y, ("•  " if i == 0 else "    ") + w, fontsize=9, color=TEXT_2,
                    va="top", ha="left", transform=ax.transAxes)
            y -= 0.085
        y -= 0.025
        if y < 0.05:
            break


def render(data, out_path):
    people = data.get("people", [])
    fig = plt.figure(figsize=(13, 7.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1], width_ratios=[1.15, 1],
                          left=0.12, right=0.97, top=0.86, bottom=0.09, hspace=0.55, wspace=0.18)

    # Header: title, period, deadline countdown, status pill
    fig.text(0.02, 0.95, "TrailNet lab board", fontsize=17, color=TEXT, weight="bold")
    fig.text(0.02, 0.915, data.get("period", ""), fontsize=10.5, color=TEXT_2)
    dl = data.get("deadline")
    if dl:
        as_of = date.fromisoformat(data.get("as_of") or date.today().isoformat())
        days = (date.fromisoformat(dl["date"]) - as_of).days
        fig.text(0.97, 0.95, f"{days} days to {dl['name']}", fontsize=13, color=TEXT, ha="right", weight="bold")
        fig.text(0.97, 0.915, f"due {date.fromisoformat(dl['date']).strftime('%b %d, %Y')}",
                 fontsize=10, color=TEXT_2, ha="right")
    st = data.get("status")
    if st:
        c = STATUS.get(st.get("label", "").lower(), MUTED)
        fig.text(0.40, 0.948, f"  {st['label'].upper()}  ", fontsize=10.5, color="white", weight="bold",
                 bbox=dict(boxstyle="round,pad=0.35", fc=c, ec=c))
        fig.text(0.40, 0.913, textwrap.shorten(st.get("reason", ""), 70), fontsize=9.5, color=TEXT_2)

    ax_hours = fig.add_subplot(gs[0:2, 0])
    bar_panel(ax_hours, people, "hours", "Hours logged (self-reported, daily logs)", "h")
    ax_commits = fig.add_subplot(gs[2, 0])
    commit_people = [dict(p, note="") for p in people]
    bar_panel(ax_commits, commit_people, "commits", "Commits (git log)", "")

    ax_hi = fig.add_subplot(gs[0, 1])
    list_panel(ax_hi, "What moved", data.get("highlights", []), "Nothing recorded")
    ax_bl = fig.add_subplot(gs[1, 1])
    blockers = [f"{b['who']}: {b['what']} (since {b.get('since', '?')})" for b in data.get("blockers", [])]
    list_panel(ax_bl, "Blocked", blockers, "No open blockers")
    ax_wt = fig.add_subplot(gs[2, 1])
    waiting = [f"{w['what']} (since {w.get('since', '?')})" for w in data.get("waiting", [])]
    tasks = [f"{p['name']}: {p.get('tasks_done', 0)} done, {p.get('tasks_open', 0)} open"
             for p in people if p.get("tasks_done") or p.get("tasks_open")]
    list_panel(ax_wt, "Waiting for Dr. Chen", waiting, "Nothing waiting")

    if tasks:
        fig.text(0.02, 0.035, "Tasks:  " + "   ·   ".join(tasks), fontsize=8, color=TEXT_2)
    fig.text(0.02, 0.012,
             "Sources: daily logs (student-approved), git log, scribe's task-list and decisions-log. "
             "Hardware, reading and writing work leave no commits. Nobody is ranked.",
             fontsize=7.5, color=MUTED)
    for ax in fig.axes:
        ax.set_facecolor(SURFACE)
    fig.savefig(out_path, facecolor=SURFACE)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Render the weekly lab board.")
    ap.add_argument("input")
    ap.add_argument("--out", default="lab_board.png")
    args = ap.parse_args()
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    print(f"wrote {render(data, args.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
