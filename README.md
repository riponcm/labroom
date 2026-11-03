# LabRoom

A research group's AI workstation in team chat, built on [Switch](https://github.com/sandbox-quantum/switch) for the Flip the Switch hackathon (Nov 4 to 7, 2026).

A professor and five students share one chat room with six Claude Code agents. The agents turn meetings, papers, daily work and commits into a record the whole lab can trust, and every record a person depends on is approved by a person.

| Agent | What it does | Model |
| --- | --- | --- |
| coordinator | Routes requests to the right agent and answers from the record. Stays quiet on chatter. | Haiku 5.5 |
| scribe | Turns a meeting transcript into a summary, PROPOSED decisions the PI approves, and a task list. | Opus 5.5 |
| librarian | Scores a paper 0 to 10 against the project and tags the student it helps. | Sonnet 5.5 |
| logbook | Turns a student's private message about their day into a log entry they approve before it is shared. | Haiku 5.5 |
| reporter | Makes the weekly lab board: hours, commits, what moved, what is blocked, what waits for the PI. | Opus 5.5 |
| auditor | Checks status and risks: work without evidence, overdue tasks, stale blockers, numbers that disagree. | Opus 5.5 |

The lab, its people and its data are fictional. The demo project, TrailNet, is a camera trap that counts wildlife on the device.

## How Switch is used

- **One room, one memory.** The Switch room holds the instructions every agent reads, and three room documents: `decisions-log` and `task-list` (owned by scribe) and `daily-logs` (owned by logbook).
- **Agents hand work to each other by name.** The reporter sends evidence to the scribe to close tasks; the scribe asks the coordinator to get a human ruling on an ambiguous decision.
- **People stay in charge.** Decisions count only after the PI approves them. A daily log is shared only after the student says yes.
- **Reproducible in one step.** `switch/labroom.template.yaml` creates the room, its six agents, members, aliases and kickoff from Switch Console > Templates.

## Repository

- `docs/agents/*.md`, `docs/room_instructions.txt`: the agents' instructions (source of truth)
- `docs/LAB_RECORDS.md`: what the PI needs, what students give, the log format, the audit
- `switch/labroom.template.yaml`: the Switch template, built by `tools/build_template.py`
- `seed/`: the fictional lab's week (transcripts, chat, daily logs, papers)
- `tools/`: lab repo builder, Mattermost seeding and polish, lab board and chart renderers, scheduled posts

Work in progress: full setup steps, demo video and architecture diagram follow.
