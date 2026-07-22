"""
tests/test_diff.py

These are the five scenarios that drove the classifier's design, made real.
Each was hand-built to model a genuine agent failure, then diffed blind
against the tool -- not written to match a known-good output. When a test
here fails after a change, that is a real regression, not a fixture problem.

Run with:
    pytest tests/ -v

Or standalone (no pytest installed):
    python3 tests/test_diff.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLIGHT = ROOT / "flight.py"
EXAMPLES = ROOT / "examples"


def run_diff(good: str, bad: str) -> str:
    result = subprocess.run(
        [sys.executable, str(FLIGHT), "diff",
         str(EXAMPLES / f"{good}.flight"), str(EXAMPLES / f"{bad}.flight")],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, f"flight diff crashed: {result.stderr}"
    return result.stdout


# ---------------------------------------------------------------------------
# Scenario 1: same prompt, different model.
# Expected: model flagged as INPUT_CHANGE, real behavior divergence at the
# step where the cheaper model actually produced a different answer.
# ---------------------------------------------------------------------------
def test_model_change_is_flagged_as_input_change():
    out = run_diff("model-change-good", "model-change-bad")
    assert "INPUT_CHANGE" in out
    assert "gpt-4o" in out and "gpt-4o-mini" in out
    assert "BEHAVIOR_CHANGE" in out
    assert "first divergence: step 3" in out


# ---------------------------------------------------------------------------
# Scenario 2: same model, different system prompt.
# This is the case that FALSE-POSITIVED in the first version of the
# classifier -- it reported "step 1 diverged" when both sides had the
# identical output "Reading file.". The fix must not regress this.
# ---------------------------------------------------------------------------
def test_prompt_change_does_not_false_positive_on_identical_output():
    out = run_diff("prompt-change-good", "prompt-change-bad")
    assert "INPUT_CHANGE" in out
    assert "prompt/context" in out
    # The real divergence is downstream (step 3), NOT step 1, where outputs
    # were identical on both sides despite the differing prompt.
    assert "first divergence: step 3" in out
    # Guard against the regression directly: step 1 must not be reported
    # as a divergence between two identical "Reading file." outputs.
    assert "Reading file.\n  + step 1 LLM  out=Reading file." not in out


# ---------------------------------------------------------------------------
# Scenario 3: tool arguments changed (model chose a different query).
# Expected: classified as INPUT_CHANGE at the tool step, not misattributed
# downstream. This was a real regression caught mid-fix -- guard it.
# ---------------------------------------------------------------------------
def test_tool_argument_change_is_input_change_at_the_right_step():
    out = run_diff("tool-args-good", "tool-args-bad")
    assert "INPUT_CHANGE" in out
    assert "tool arguments changed" in out
    assert "first divergence: step 2" in out
    assert "database_query" in out


# ---------------------------------------------------------------------------
# Scenario 4: long chain (9 steps), divergence buried at step 8.
# This is where logs fail hardest and a diff should win hardest. Also a
# real regression: the first classifier version reported "no divergence"
# here (false negative) because it didn't treat tool-arg changes as input.
# ---------------------------------------------------------------------------
def test_deep_divergence_in_long_chain_is_not_missed():
    out = run_diff("long-chain-good", "long-chain-bad")
    assert "No divergence" not in out          # guards the false-negative bug
    assert "first divergence: step 8" in out
    assert "charge_customer" in out
    assert "123" in out and "321" in out


# ---------------------------------------------------------------------------
# Scenario 5: identical model, identical prompt, identical tool arguments --
# the tool itself returned a different result. This is the pure causal case
# ("the world was held constant and the agent still behaved differently")
# and the one the whole classifier exists to isolate correctly.
# ---------------------------------------------------------------------------
def test_pure_behavior_change_with_identical_input():
    out = run_diff("auth-failure-good", "auth-failure-bad")
    assert "BEHAVIOR_CHANGE" in out
    assert "identical arguments" in out
    assert "first divergence: step 2" in out
    assert "search_customer" in out
    # Must NOT be reported as an input change -- args are identical here.
    assert 'in={"id": 123}' in out
    assert out.count('in={"id": 123}') == 2   # both sides, same args


# ---------------------------------------------------------------------------
# Sanity: convert + show should not crash on any example pair, and show
# output should render every step without throwing.
# ---------------------------------------------------------------------------
def test_show_runs_cleanly_on_all_examples():
    for f in EXAMPLES.glob("*.flight"):
        result = subprocess.run(
            [sys.executable, str(FLIGHT), "show", str(f)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, f"flight show crashed on {f.name}: {result.stderr}"
        assert "RUN" in result.stdout


if __name__ == "__main__":
    # Allow running without pytest installed.
    fails = 0
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            fails += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests)-fails}/{len(tests)} passed")
    sys.exit(1 if fails else 0)
