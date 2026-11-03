#!/usr/bin/env python3
"""Render the Reporter's weekly contribution chart as a PNG.

The agent writes a small JSON file, then runs this script. The chart shows one
group of bars per person (commits and tasks done) with a note under anyone who
had a known absence or blocker, so a low count always carries its reason.

Input JSON:
{
  "period": "Oct 27 to Oct 31, 2026",
  "people": [
    {"name": "Sofia Alvarez", "workstream": "data", "commits": 10, "tasks_done": 3,
     "tasks_open": 0, "note": ""},
    ...
  ]
}

Usage:
    python tools/progress_chart.py progress.json --out progress.png
"""

import argparse
import json
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Validated categorical palette (slot 1 blue, slot 2 orange) on a light surface.
COMMITS = "#2a78d6"
TASKS = "#eb6834"
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"


def render(data, out_path, title=None):
    people = data["people"]
    n = len(people)
    names = [p["name"] for p in people]
    commits = [int(p.get("commits", 0)) for p in people]
    tasks = [int(p.get("tasks_done", 0)) for p in people]
    notes = [p.get("note", "") or "" for p in people]
    streams = [p.get("workstream", "") or "" for p in people]

    width = 0.32
    xs = list(range(n))
    fig, ax = plt.subplots(figsize=(max(7, 1.5 * n), 4.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    b1 = ax.bar([x - width / 2 - 0.01 for x in xs], commits, width, color=COMMITS, label="commits", zorder=3)
    b2 = ax.bar([x + width / 2 + 0.01 for x in xs], tasks, width, color=TASKS, label="tasks done", zorder=3)

    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.15, f"{int(h)}",
                        ha="center", va="bottom", fontsize=8, color=TEXT_2)

    labels = []
    for name, stream, note in zip(names, streams, notes):
        label = name
        if stream:
            label += f"\n{stream}"
        if note:
            label += "\n" + "\n".join(textwrap.wrap(note, 18))
        labels.append(label)
    ax.set_xticks(xs, labels, fontsize=8, color=TEXT)

    ymax = max(commits + tasks + [1])
    ax.set_ylim(0, ymax * 1.25)
    ax.set_ylabel("count, last 7 days", fontsize=9, color=TEXT_2)
    ax.yaxis.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TEXT_2, length=0)

    ax.set_title(title or f"TrailNet lab activity, {data.get('period', '')}", loc="left", fontsize=11, color=TEXT)
    ax.legend(frameon=False, fontsize=8, loc="upper right", labelcolor=TEXT_2)
    fig.text(0.01, 0.01, "Commits from git log; tasks from the room task list. Notes give the reason behind low counts.",
             fontsize=7, color=TEXT_2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out_path, facecolor=SURFACE)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Render the weekly contribution chart.")
    ap.add_argument("input", help="JSON file written by the agent")
    ap.add_argument("--out", default="progress.png", help="PNG path to write")
    ap.add_argument("--title", default=None)
    args = ap.parse_args()
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    out = render(data, args.out, args.title)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
