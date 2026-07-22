# The `.flight` format (DRAFT — pre-validation)

> **Status: draft, not yet a spec.** This describes the format as implemented
> today. It has not yet survived contact with a developer outside this
> project. Expect it to change. Do not build against this as a stable
> interface yet — track `flight.py`'s `_classify_step` as the source of truth
> until this doc is promoted.

## Why a format, not just a tool

The long-term bet here is not the CLI. `flight show` and `flight diff` are
the first two consumers of an artifact — the same way `git log` and `git
diff` are two consumers of the git object format. If `.flight` is useful,
other tools (IDE plugins, CI checks, framework-native exporters) should be
able to read and write it without going through this repository's code.

That only works if the format is boring and stable. It is not stable yet.

## Shape

```json
{
  "version": "flight/v1",
  "run_id": "string, unique per execution",
  "model": "string, the model identifier used in this run",
  "events": [
    { "seq": 1, "type": "llm",  "input": "string", "output": "string" },
    { "seq": 2, "type": "tool", "name": "string", "input": "string", "output": "string" }
  ]
}
```

### Fields

- **`version`** — always `"flight/v1"` for this draft. Breaking changes bump
  this string; nothing reads a `.flight` file without checking it first.
- **`run_id`** — arbitrary string, unique to one execution. No format is
  imposed; adapters may use the source framework's trace ID.
- **`model`** — the model identifier active for the run. Runs that swap
  models mid-execution are not yet represented (open question, see below).
- **`events`** — an ordered list. `seq` is 1-indexed and must be contiguous;
  `diff` aligns two runs by walking `events` in lockstep by index, not by
  matching `seq` values, so gaps are tolerated but not yet meaningful.

### Event types

**`llm`** — one model call.
- `input` — flattened prompt/context sent to the model, as plain text.
- `output` — the model's response, as plain text.

**`tool`** — one tool/function call.
- `name` — the tool name as called.
- `input` — arguments, currently serialized as a JSON string.
- `output` — the tool's return value, currently serialized as text.

## What this format deliberately does NOT capture (yet)

Being honest about the gaps matters more than pretending they're solved:

- **Timestamps / latency.** Not in v1. Needed eventually for anything
  performance-related; irrelevant to the divergence question v1 answers.
- **Cost / token counts.** Same as above.
- **Streaming.** Events are captured as complete request/response pairs.
  A real capture proxy will need to decide whether to store the reassembled
  result (likely) or the raw stream (probably not, per "boring schema").
- **Parallel tool calls.** The lockstep alignment in `diff` assumes one
  event happens after another. Agents that fire tools concurrently will
  need a documented ordering rule before this format can honestly claim
  framework-agnostic support.
- **Nested/sub-agent runs.** Out of scope for v1. A run is flat.
- **Model changing mid-run.** The schema has one top-level `model` field.
  If a real framework hands off between models inside one run, this format
  cannot yet represent that faithfully.

None of these are hard blockers for the current hypothesis test. They are
listed here so the first thing that breaks when someone else uses this
isn't a surprise to them or to us.

## Divergence classification (implemented in `python3 flight.py diff`)

Every difference between two runs' events is classified into exactly one of:

- **`INPUT_CHANGE`** — the model, the prompt/context, or the arguments fed
  into a step differ. This is a cause, not a divergence in behavior.
- **`BEHAVIOR_CHANGE`** — a step received identical input in both runs but
  produced a different output. This is the causally interesting case.
- **`DOWNSTREAM_EFFECT`** — implicit: once a divergence is found, every
  later difference is treated as downstream of it. `diff` does not currently
  re-classify later steps individually once a first divergence is found.

This three-way split exists because collapsing "input changed" and
"behavior changed" into one signal produces false positives (a step looks
like "the divergence" when it's actually just downstream of a prompt edit
reported already) — this was found and fixed during testing, see the
project README.

## Versioning

Anything that changes the meaning of an existing field, or the alignment
rule `diff` uses, is a new `version` string. Anything that only adds an
optional field is not.
