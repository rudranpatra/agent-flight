# flight

Your coding agent fixed the auth bug yesterday. Today, same prompt, it says the bug doesn't exist.

You open the logs. Thousands of lines. Somewhere in there is the one step that actually changed — but finding it means reading everything and guessing.

```
$ flight diff examples/auth-failure-good.flight examples/auth-failure-bad.flight

AI EXECUTION DIFFERENCE
============================================================
BEHAVIOR_CHANGE  (same input, different result)
  first divergence: step 2
  reason: tool returned a different result for identical arguments
  - step 2 TOOL search_customer  in={"id": 123}  out=customer found: active
  + step 2 TOOL search_customer  in={"id": 123}  out=ERROR: customer service unavailable

DOWNSTREAM_EFFECT: all later differences originate here.
```

Same arguments, different result, one line telling you exactly where. That's the whole tool.

Your code has `git diff`. Your infrastructure has `terraform plan`. Your AI agents have logs. `flight` is the missing one: **`git blame` for AI runs** — the exact step where behavior diverged, not a guess about why.

No AI in the loop. No dashboard. No account. The machine shows evidence; you decide.

---

## How it classifies a divergence

Every difference between two runs falls into one of three buckets, so you never mistake a cause for an effect:

- **INPUT_CHANGE** — the world changed. A different model, an edited prompt, or different tool arguments the model chose upstream. This is a *cause*, not a divergence.
- **BEHAVIOR_CHANGE** — identical input into a step, different output. This is the interesting, causal case — the one in the example above.
- **DOWNSTREAM_EFFECT** — later steps differ only because an earlier change pushed the chain apart. Everything traces back to the first divergence.

`flight` diffs *runtime executions*, not agent definitions or code authorship. It answers "what did the agent **do** differently," not "what did I change about the agent."

---

## Why this exists

Developers already reach for a diff when something changes: `git diff`, `terraform plan`, `kubectl diff`. Agent executions are the one place with no equivalent — a run happens, something goes wrong, and the reasoning evaporates into logs nobody can reconstruct.

Existing agent-observability tools (LangSmith, Langfuse, Phoenix, Helicone) are trace *viewers*. `flight` is not a viewer. It answers one question: **what changed between the run that worked and the run that didn't.** That's a diff, not a dashboard.

Two deliberate non-goals, because they are how this kind of tool loses trust:

- **No "likely cause" narration.** `flight` never asks a model to explain a model. It shows the structural delta and stops. (LLM-judge failure attribution scores ~14% step-level accuracy — using AI to debug AI compounds uncertainty instead of resolving it.)
- **No replay-as-reproduction promise.** LLM inference is non-deterministic even at temperature 0. `flight` diffs *recorded* runs; it does not claim to re-derive what a model *would* do.

---

## Install

Python 3.8+. Zero dependencies.

```bash
pip install agent-flight          # once published to PyPI
# or, from this repo:
pip install -e .
```

## Commands

Three, and only three.

```bash
flight convert <trace.json> <out.flight>   # normalize a framework trace -> flight/v1
flight show    <run.flight>                # human-readable step list
flight diff    <a.flight> <b.flight>       # structural diff, first divergence
```

### convert

Turns an agent framework's trace into a portable `flight/v1` artifact. Today: OpenAI Agents SDK. (LangChain and Claude Code adapters are next.)

```bash
flight convert run.json run.flight
# wrote run.flight  (5 events, model=gpt-4o)
```

### show

```bash
flight show examples/model-change-bad.flight
```
```
RUN t1-bad   model=gpt-4o-mini   (4 steps)
------------------------------------------------------------
  1 LLM
      in : system: You are a coding agent. user: Fix the auth bug…
      out: I'll read auth.py first.
  2 TOOL  read_file()
      in : {"path": "auth.py"}
      out: def verify(t): return t.exp > now()
  ...
```

### diff

The whole point. Reports model change, prompt/context delta, and the **first step where behavior diverged**.

```bash
flight diff examples/auth-failure-good.flight examples/auth-failure-bad.flight
```

---

## The `flight/v1` artifact

Deliberately boring. No universal ontology — that's a trap that eats months before the command is useful.

```json
{
  "version": "flight/v1",
  "run_id": "abc123",
  "model": "gpt-4o",
  "events": [
    { "seq": 1, "type": "llm",  "input": "...", "output": "..." },
    { "seq": 2, "type": "tool", "name": "database_query", "input": "...", "output": "..." }
  ]
}
```

The artifact is the product. `convert` produces it; `show` and `diff` only ever touch it. Adding a new framework means writing one adapter to this shape — nothing downstream changes.

---

## Status — read this before trusting it

This is a **value-hypothesis prototype**, not a product. It was built to answer one question in a day: *does an AI execution diff create a new debugging reflex, or is it a demo that impresses once and gets uninstalled?*

Five scenarios, each hand-built to model a real failure and diffed blind — committed as real, runnable tests, not conversation output:

```bash
python3 tests/test_diff.py     # no pytest required
# or: pytest tests/ -v
```

| Scenario (`examples/`) | Result |
|---|---|
| `model-change-*` — same prompt, different model | ✅ Flags model change as INPUT_CHANGE + behavior divergence at the exact step |
| `prompt-change-*` — same model, different prompt | ✅ Classifies prompt edit as cause, isolates the real divergence downstream |
| `tool-args-*` — tool arguments changed | ✅ Attributes to the step where args diverged |
| `long-chain-*` — divergence buried at step 8/9 | ✅ Surfaces the deep change; no false negative |
| `auth-failure-*` — identical input, different tool output | ✅ Correctly isolates BEHAVIOR_CHANGE — the causal case |

**Not yet built (and deliberately deferred):** the capture proxy. `flight` currently normalizes traces that frameworks already emit (adapter today: OpenAI Agents SDK). A framework-agnostic recording proxy is the distribution bet — it only gets built once the diff proves worth distributing.

**Honest limits.** The classifier attributes the *first structural divergence*; it does not prove causation across non-deterministic model calls, and it will not tell you *why* the model chose differently — only that it did. It never asks a model to explain a model.

---

## Repo status

This repo is **private, pre-launch**. The format (`docs/flight-format.md`)
is marked draft on purpose — it has not yet survived a developer outside
this project reading it cold. Before this goes public:

- [ ] Run `docs/STRANGER_TEST.md` against 3 people, 3 scenarios each
- [ ] Fix whatever confuses them
- [ ] Promote the format doc from draft once it holds

See `docs/STRANGER_TEST.md` for the exact protocol and pass/fail bar.

---

## What this is not

- Not an observability platform.
- Not a SaaS. No server, no account, no cloud.
- Not an agent framework or an eval harness.
- Not an AI that tells you what's wrong. It shows you what changed.

If any of those creep into v0, it stops being a diff and becomes another thing that already exists.

## License

MIT (intended).
