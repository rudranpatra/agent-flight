STRANGER TEST — read this before you run it, not after
=========================================================

Purpose: find out if `python3 flight.py diff` explains an AI agent failure to someone
who did NOT build this, without you saying anything beyond the prompt below.

Do not explain INPUT_CHANGE / BEHAVIOR_CHANGE / DOWNSTREAM_EFFECT first.
Do not explain the scenario first. If they ask what a term means, say
"whatever you think it means" and write down that they asked.

STEP 1 — Hand them two files, nothing else:
    examples/auth-failure-good.flight
    examples/auth-failure-bad.flight

STEP 2 — Say exactly this, then stop talking:
    "This is a customer-support agent. One run worked, one didn't.
     Figure out why, using this tool. Talk out loud while you do it."

    $ python3 flight.py diff examples/auth-failure-good.flight examples/auth-failure-bad.flight

STEP 3 — Start a timer. Write down:
    - Time until they say what went wrong, in their own words
    - Any term they had to ask you to explain
    - Anything they expected to see that wasn't there
    - Their unprompted reaction (bored / mildly interested / "oh that's useful")

PASS bar (from the project's own gate):
    Under 60 seconds to a correct plain-English explanation of the failure,
    with zero clarifying questions about what the output means.

FAIL signals, each one is real data, write it down verbatim:
    - "What am I looking at?"
    - They read the reason line but can't say what it means for their agent
    - They ask whether INPUT_CHANGE or BEHAVIOR_CHANGE is "the bug"
    - They want to know why args changed (the tool doesn't say — it can't)

STEP 4 — Repeat with:
    examples/model-change-good.flight / model-change-bad.flight
    examples/tool-args-good.flight / tool-args-bad.flight

Three people, three scenarios each, is enough data to decide. More than
five people before making a decision is procrastination dressed as rigor.

WHAT TO DO WITH THE RESULT
---------------------------
3/3 pass, all three scenarios: promote docs/flight-format.md from draft,
make the repo public, proceed to the launch sequence.

Any fail: fix the confusing thing BEFORE making the repo public. A public
repo with a known point of confusion is worse than a private repo without
one — it spends the one-time launch attention on a demo that doesn't land.

Do not run this test on yourself. You already know the answer.
