# Lab records: what the professor needs, what students give

The question behind this design: in a research lab, what does the PI actually need to see each week, and what is the smallest thing a student can give each day that answers it? LabRoom turns a two-minute daily message into that record, and two agents read it back as a progress board and an audit.

## What the PI needs

| Need | Question the PI asks | Where the answer comes from |
| --- | --- | --- |
| Status against the deadline | "Are we on track for Dec 1?" | Auditor, from tasks, logs and results |
| What moved | "What got done last week?" | Reporter's lab board, from logs, commits and tasks |
| What is stuck | "Who is blocked, on what, since when?" | Blockers in daily logs and chat |
| Decisions waiting for them | "What do I need to approve?" | Scribe's decisions-log, status PROPOSED |
| Who works on what | "Who owns each part, and is anything unowned?" | Workstream on every log, task and commit |
| Effort | "Where is the time going?" | Hours per workstream from daily logs (self-reported, optional) |
| Evidence | "Show me the result, not the claim" | Commit hashes, files, experiment ids and numbers in each log |
| Paper material | "What can go in the paper?" | Results in logs, librarian's paper records |

## What a student gives

One message a day, in their own words, sent privately to the logbook agent. For example:

> today: reran night test on v0.3, 160 night frames, day 88.3 night 73.1, took ~2.5h. added per-class recall to the eval csv 1.5h. pushed both. tomorrow per-site breakdown for wei. no blockers

The logbook agent turns it into a standard entry, shows the draft to the student in the private chat, and only after the student says "yes" posts it to the lab room and the record. The raw message stays private. The student always approves their own record.

## Daily log entry format

```
📒 Daily log · Tue Nov 3, 2026 · Priya Nair · model and quantization · 4.0 h
Done
  • Reran the night test on the v0.3 split (160 night frames): day 88.3, night 73.1 · 2.5 h
  • Added per-class recall to the eval CSV · 1.5 h
Evidence: commits 3f2a1c9, 7d0e4b2 · model/results.md
Blockers: none
Next: per-site night breakdown for Wei
```

Rules the logbook follows:

- Hours are the student's own numbers. It never estimates. If none are given it asks once, then writes "hours not given".
- Evidence is what the student names, plus commit hashes it finds with `git log --author` for that day, and it says when it added them.
- A blocker that needs the PI (money, approval, a deadline change) gets a line "Needs Dr. Chen:" and tags her.
- It never comments on how much work someone did.

## Where the records live

| Record | Owner | Store |
| --- | --- | --- |
| decisions-log | scribe | Switch room document; each decision PROPOSED, APPROVED or REJECTED |
| task-list | scribe | Switch room document; owner, due date, status |
| daily-logs | logbook | Switch room document, plus one JSON line per entry in `out/daily_logs.jsonl` for charts |
| paper records | librarian | Room history, one "Record:" line per paper |
| lab board | reporter | PNG attached in the room, rendered by `tools/lab_board.py` |
| audit | auditor | Room post, plus `out/audit_<date>.json` |

## The audit

The auditor answers "what is going on, who did what, and is it on track". Its report has five parts:

1. **Status.** One line: on track or at risk for the Dec 1 paper, and why.
2. **By workstream.** Owner, hours logged, commits, tasks done and open, latest result, last activity.
3. **Checks.** Only the ones that apply: work logged without evidence; tasks past due; decisions PROPOSED for more than two days; blockers open more than two days; no log for three working days without a known reason; numbers that disagree between logs, chat and the repository.
4. **Needs Dr. Chen.** Decisions and blockers only the PI can resolve.
5. **Up to three recommendations.**

Every claim cites its source: a log date, a commit hash, a message time.

## Guardrails against surveillance

- No agent ranks or scores people.
- A low number always comes with its reason, or with "reason unknown, ask".
- Hardware, reading and writing work leave no commits. Missing commits are never treated as missing work.
- Hours are optional and self-reported. The student approves every entry before anyone sees it.
- Everyone in the lab sees the same records, the PI included. There is no private channel about students.

## Meetings, announcements and private notes

The organizer acts for the PI. Switch agents cannot pin a post or open a private chat with a person, so `tools/lab_actions.py` does those two things with the PI's delegated account, only when the PI asked, and logs every action to `out/actions.log`.

| The PI says | What happens |
| --- | --- |
| "Post an announcement: ..." | A short, clear notice in the lab room, pinned |
| "Schedule the group meeting Thu 10:00 to 10:45, link ..., agenda ..." | A pinned notice with a numbered agenda (owner, minutes) and a "Before the meeting" list built from the records; everyone tagged; registered in `out/meetings.json` |
| (lab clock, 15 min before) | "⏰ starts in 15 minutes", attendees tagged |
| (lab clock, at the start) | "▶️ starting now" with the link |
| (lab clock, 5 min after the end) | "✅ is over: attach the transcript and tag the scribe", then the notice is unpinned |
| "Send Lucas a private message: ..." (PI only) | A short message in her voice in Lucas's private chat, signed "sent for Dr. Chen by the lab organizer" |

Only Dr. Chen or Priya can ask for announcements and meetings, and only Dr. Chen for private messages. The organizer refuses anyone else.

## Automation

- `tools/lab_clock.py` runs in a terminal and nudges the organizer at meeting times through a private chat, so the lab room only sees the organizer's posts.
- Weekdays at 17:00, a scheduled post asks the logbook to remind anyone who hasn't logged today.
- Mondays at 09:00, a scheduled post asks the reporter for last week's lab board and the auditor for the weekly audit.
- Both are Windows scheduled tasks (`tools/schedule_lab.ps1`), because Switch has no scheduler of its own.
