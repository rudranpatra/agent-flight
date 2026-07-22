# LinkedIn post — final version

AI agents have a debugging problem nobody talks about.

When regular software breaks, we have:

→ `git diff`
→ `git blame`
→ stack traces
→ commit history

We can answer: *what changed?*

When an AI agent breaks, we have logs. Thousands of lines of them.

The model changed. The prompt changed. A tool returned something different. Somewhere in that chain is the one step that actually caused the failure — and finding it means reading logs for an hour and guessing.

I built a tiny experiment: what if two AI executions could be diffed the way two commits can?

Not a dashboard. Not another observability platform.

A portable artifact for one execution, and a diff between two — that separates "the input/prompt/model changed" from "identical input produced a different result."

No AI explaining AI.
No "here's what probably went wrong."
Just the exact step where behavior diverged, and the evidence. You decide what it means.

Git blame for AI runs.

It's still early. The README works, the tests pass, and the only thing I actually trust now is watching someone try it cold.

If you build with AI agents and want to be one of the people who tells me whether this is a reflex you'd actually reach for — comment or DM me and I'll send the repo.

---

# Alternative — original draft

AI agents have a debugging problem nobody talks about.

When regular software breaks, we have:
→ git diff
→ git blame
→ stack traces
→ commit history

We can answer: "what changed?"

When an AI agent breaks, we have logs. Thousands of lines of them.
The model changed. The prompt changed. A tool returned something different.
Somewhere in there is the one step that actually caused the failure —
and finding it means reading logs for an hour and guessing.

We're exploring something simple: what if two AI executions could be
diffed the way two commits can?

Not a dashboard. Not another observability platform.
A portable artifact for one execution, and a diff between two of them —
that separates "the model/prompt/input changed" (a cause) from
"identical input produced a different result" (the actual divergence).

No AI explaining AI. No "here's what probably went wrong."
Just: here's the exact step where behavior diverged, and here's the
evidence. You decide what it means.

Git blame for AI runs.

Still early. Still testing whether this is a reflex developers actually
reach for, or just an interesting idea. Building in public — will share
what we find.
