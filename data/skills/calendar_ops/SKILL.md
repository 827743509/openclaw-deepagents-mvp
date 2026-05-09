---
name: calendar-ops
description: Use this skill for scheduling, creating calendar events, listing events, resolving time ambiguity, and setting reminders.
---

# Calendar Operations Skill

## Rules

- Always resolve relative dates into absolute dates when possible.
- Ask or infer timezone. Default to the user's local timezone if configured by the app.
- Before creating an event, show:
  - title
  - start time
  - end time
  - location
  - notes
- Create reminders when the task is one-way and does not need a meeting slot.
