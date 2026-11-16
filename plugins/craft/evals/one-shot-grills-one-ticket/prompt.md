---
max_turns: 12
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
runs: 1
---
Run craft:spec on the one-shot plan CRAFT-900.

This is a test session: Linear and subagents are not reachable. Treat every Linear move and comment as done, and use the state below instead of reading Linear.

Plan ticket CRAFT-900, `mode=one-shot`, plan document "Plan: Nap Time v1". An earlier spec session of this plan stopped before it asked anything. No ticket has a spec yet. Its tickets, in build order, with no blockers, are all in **Specifying**, and that session's spec scouts returned these open questions:

1. CRAFT-901 Share the family.
   - Settings while the invite is not opened yet. Recommended: "Invite sent. Waiting for your partner to open the link." Medium certainty.
   - Children the partner added before joining. Recommended: they stay on the partner's phone only. Low certainty.
2. CRAFT-902 Sleep timer on the Lock Screen.
   - After "Awake". Recommended: the Live Activity closes at once. Medium certainty.
   - Nights longer than 8 hours, when iOS ends the Live Activity. Recommended: accept it. Low certainty.
3. CRAFT-903 Nudges.
   - What stops the bedtime nudge. Recommended: any sleep started since 18:00. Medium certainty.
   - When to ask for notification permission. Recommended: on the first "Sleep time" tap. Low certainty.

Go on with the loop, and end with your next chat message to the owner.
