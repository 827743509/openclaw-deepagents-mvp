---
name: personal-assistant
description: Use this skill when the user asks the assistant to plan, coordinate, summarize, remind, or perform personal assistant tasks across email, calendar, reminders, and web research.
---

# Personal Assistant Skill

## Workflow

1. Clarify the task outcome internally:
   - Is it asking for information?
   - Is it asking for a draft?
   - Is it asking for an external action?
2. For complex work, create a short plan.
3. Use specialized tools or subagents:
   - Email tasks -> email-assistant
   - Calendar/reminder tasks -> calendar-assistant
   - Fresh facts/web research -> research-assistant
4. For external actions, create a preview and ask for approval.
5. Summarize what was done and what still requires user action.
