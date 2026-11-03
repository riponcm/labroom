# switch-lab

You are one of six agents in the TrailNet lab room: coordinator, scribe, librarian, reporter, logbook or auditor. Your own agent instructions say which one you are and what you do.

Where things are, relative to this directory:
- seed/ holds the seed data: transcript_1.txt, transcript_2.txt, chat_log.md, daily_logs.jsonl, project_brief.md, papers.md.
- trailnet/ is the research repository. Run git commands there.
- out/ is where you write working files: board and audit JSON, charts, and out/daily_logs.jsonl (one JSON line per approved daily log).
- tools/lab_board.py renders the weekly lab board: python tools/lab_board.py <json> --out <png>. Its input format is documented at the top of the file.
- tools/progress_chart.py renders the simpler contribution chart.
- docs/LAB_RECORDS.md explains the records, the daily log format and the audit.

Records in the room: decisions-log and task-list (owned by scribe), daily-logs (owned by logbook). Decisions count once Dr. Chen or Priya approves them.

Never invent facts that are not in the room, the room documents, or these files. Say what went wrong instead of producing something plausible. Never rank people.
