#!/usr/bin/env python3
"""
flight — diff for machine decisions.

Value-hypothesis prototype. Three commands, one adapter, zero deps, zero AI.
The machine shows evidence. Humans decide.

    flight convert <trace.json> <out.flight>   # OpenAI Agents SDK trace -> flight/v1
    flight show    <run.flight>                # human-readable step list
    flight diff    <a.flight> <b.flight>       # structural diff, first divergence

Design rules held from the debate:
  - Deterministic. No model calls. No "likely cause" narration.
  - The artifact is the product. convert/show/diff only touch flight/v1.
  - Boring schema. No universal ontology.
"""

import json, sys, hashlib, difflib

# ----------------------------------------------------------------------------
# flight/v1 schema (deliberately boring)
#   { version, run_id, model, events: [ {seq, type, ...} ] }
#   type == "llm":  {seq, type:"llm",  input, output}
#   type == "tool": {seq, type:"tool", name, input, output}
# ----------------------------------------------------------------------------

def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()[:12]

# ---- ADAPTER: OpenAI Agents SDK trace -> flight/v1 -------------------------
# Real Agents SDK traces are a list of spans; each span has span_data with a
# `type` ("generation" | "function" | ...). We normalize to llm/tool events.
# This is intentionally a ~50-line function, not a proxy.

def convert_openai_agents(trace: dict) -> dict:
    spans = trace.get("spans") or trace.get("data") or []
    model = None
    events, seq = [], 0

    for sp in spans:
        sd = sp.get("span_data", sp)
        t = sd.get("type")

        if t == "generation":
            model = model or sd.get("model")
            # input: list of {role, content} messages
            msgs = sd.get("input") or []
            inp = "\n".join(
                f"{m.get('role','?')}: {_content_text(m.get('content'))}" for m in msgs
            )
            out_msgs = sd.get("output") or []
            out = "\n".join(_content_text(m.get("content")) for m in out_msgs)
            seq += 1
            events.append({"seq": seq, "type": "llm", "input": inp, "output": out})

        elif t == "function":
            seq += 1
            events.append({
                "seq": seq, "type": "tool",
                "name": sd.get("name", "?"),
                "input": _as_text(sd.get("input")),
                "output": _as_text(sd.get("output")),
            })

    return {
        "version": "flight/v1",
        "run_id": trace.get("trace_id") or trace.get("run_id") or _h(json.dumps(spans)[:2000]),
        "model": model or "unknown",
        "events": events,
    }

def _content_text(c):
    if c is None: return ""
    if isinstance(c, str): return c
    if isinstance(c, list):
        return " ".join(
            (p.get("text","") if isinstance(p, dict) else str(p)) for p in c
        )
    return str(c)

def _as_text(x):
    if x is None: return ""
    if isinstance(x, str): return x
    return json.dumps(x, sort_keys=True)

# ---- COMMAND: convert ------------------------------------------------------

def cmd_convert(src, dst):
    with open(src) as f:
        trace = json.load(f)
    run = convert_openai_agents(trace)
    with open(dst, "w") as f:
        json.dump(run, f, indent=2)
    print(f"wrote {dst}  ({len(run['events'])} events, model={run['model']})")

# ---- COMMAND: show ---------------------------------------------------------

def cmd_show(path):
    run = json.load(open(path))
    print(f"RUN {run['run_id']}   model={run['model']}   ({len(run['events'])} steps)")
    print("-" * 60)
    for e in run["events"]:
        if e["type"] == "llm":
            print(f"{e['seq']:>3} LLM")
            print(f"      in : {_snip(e['input'])}")
            print(f"      out: {_snip(e['output'])}")
        else:
            print(f"{e['seq']:>3} TOOL  {e['name']}()")
            print(f"      in : {_snip(e['input'])}")
            print(f"      out: {_snip(e['output'])}")

def _snip(s, n=72):
    s = (s or "").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"

# ---- COMMAND: diff ---------------------------------------------------------

def cmd_diff(pa, pb):
    a = json.load(open(pa))
    b = json.load(open(pb))

    print("AI EXECUTION DIFFERENCE")
    print("=" * 60)

    ea, eb = a["events"], b["events"]

    # ------------------------------------------------------------------
    # Three-category classification. Never blur input change with behavior
    # divergence.
    #   A) INPUT_CHANGE      - the world changed (model swap, prompt/context
    #                          edit). A cause, not a divergence.
    #   B) BEHAVIOR_CHANGE   - same inputs into a step, different output/action.
    #                          The interesting, causal case.
    #   C) DOWNSTREAM_EFFECT - steps differ, but only because an earlier
    #                          BEHAVIOR_CHANGE pushed the chain apart.
    # ------------------------------------------------------------------

    # Global input changes (whole-run causes) -------------------------
    model_changed = a["model"] != b["model"]
    prompt_delta = _prompt_delta_lines(ea, eb)

    # Find the FIRST *meaningful* step divergence, then classify WHY.
    #   INPUT_CHANGE  -> the action/args fed into the step differ
    #                    (the model chose differently upstream)
    #   BEHAVIOR      -> identical input into the step, different output/result
    # We skip steps whose ONLY difference is a prompt/context edit already
    # reported at the run level AND whose output is identical -- announcing
    # those as "the divergence" is the confusing false positive we killed.
    run_level_prompt = bool(prompt_delta)
    first = None
    for i in range(min(len(ea), len(eb))):
        x, y = ea[i], eb[i]
        cls, why = _classify_step(x, y)
        if not cls:
            continue
        only_prompt_noise = (
            run_level_prompt and x["type"] == "llm"
            and x.get("input") != y.get("input")
            and x.get("output") == y.get("output")
        )
        if only_prompt_noise:
            continue          # not a real divergence; keep looking
        first = (i + 1, x, y, cls, why)
        break

    # Report -----------------------------------------------------------
    if model_changed or prompt_delta:
        print("INPUT_CHANGE  (whole-run cause, not a divergence)")
        if model_changed:
            print(f"  model:  {a['model']}  ->  {b['model']}")
        if prompt_delta:
            print("  prompt/context (first LLM step):")
            for line in prompt_delta:
                print(f"    {line}")
        print()

    if first:
        seq, x, y, cls, why = first
        header = ("INPUT_CHANGE  (step input differs)" if cls == "input"
                  else "BEHAVIOR_CHANGE  (same input, different result)")
        print(header)
        print(f"  first divergence: step {seq}")
        print(f"  reason: {why}")
        print(f"  - {_describe(x)}")
        print(f"  + {_describe(y)}")
        print()
        print("DOWNSTREAM_EFFECT: all later differences originate here.")
    elif len(ea) != len(eb):
        print("BEHAVIOR_CHANGE  (chain length differs)")
        print(f"  first divergence: step {min(len(ea),len(eb))+1}")
        print(f"  reason: one run has more steps ({len(ea)} vs {len(eb)})")
    elif not (model_changed or prompt_delta):
        print("No divergence. Runs are step-identical.")
    print()

def _classify_step(x, y):
    """Return (category, reason) for the first way two aligned steps differ,
    or (None, None) if identical. category in {'input','behavior'}."""
    if x["type"] != y["type"]:
        return "input", f"step type changed ({x['type']} -> {y['type']})"
    if x["type"] == "tool":
        if x.get("name") != y.get("name"):
            return "input", f"different tool called ({x.get('name')} -> {y.get('name')})"
        if x.get("input") != y.get("input"):
            return "input", "tool arguments changed (model chose different args upstream)"
        if x.get("output") != y.get("output"):
            return "behavior", "tool returned a different result for identical arguments"
    else:  # llm
        if x.get("input") != y.get("input"):
            return "input", "model input (prompt/context) changed"
        if x.get("output") != y.get("output"):
            return "behavior", "model produced a different output for identical input"
    return None, None

def _prompt_delta_lines(ea, eb):
    la = next((e for e in ea if e["type"] == "llm"), None)
    lb = next((e for e in eb if e["type"] == "llm"), None)
    if not (la and lb) or la["input"] == lb["input"]:
        return []
    diff = difflib.unified_diff(
        la["input"].splitlines(), lb["input"].splitlines(), lineterm="", n=0,
    )
    return [ln for ln in list(diff)[2:] if ln and ln[0] in "+-"]

def _describe(e):
    if e["type"] == "tool":
        return f"step {e['seq']} TOOL {e.get('name')}  in={_snip(e.get('input'),40)}  out={_snip(e.get('output'),40)}"
    return f"step {e['seq']} LLM  out={_snip(e.get('output'),50)}"

# ---- entrypoint ------------------------------------------------------------

def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return
    if a[0] == "convert" and len(a) == 3: cmd_convert(a[1], a[2])
    elif a[0] == "show" and len(a) == 2:  cmd_show(a[1])
    elif a[0] == "diff" and len(a) == 3:  cmd_diff(a[1], a[2])
    else:
        print(__doc__); sys.exit(1)

if __name__ == "__main__":
    main()
