import json

def gen(model, msgs, out): return {"type":"generation","model":model,"input":msgs,"output":[{"content":out}]}
def fn(name, inp, out):    return {"type":"function","name":name,"input":inp,"output":out}
def trace(tid, spans):     return {"trace_id":tid,"spans":[{"span_data":s} for s in spans]}

SYS = "You are a coding agent."
TASK = "Fix the authentication bug in auth.py"

# ---- Test 1: same prompt, DIFFERENT MODEL ----
base_msgs = [{"role":"system","content":SYS},{"role":"user","content":TASK}]
t1_good = trace("t1-good",[
    gen("gpt-4o", base_msgs, "I'll read auth.py first."),
    fn("read_file", {"path":"auth.py"}, "def verify(t): return t.exp > now()"),
    gen("gpt-4o", base_msgs, "Token expiry uses seconds. I'll fix it."),
    fn("edit_file", {"path":"auth.py","patch":"exp*1000"}, "ok"),
    fn("run_tests", {}, "PASSED"),
])
t1_bad = trace("t1-bad",[
    gen("gpt-4o-mini", base_msgs, "I'll read auth.py first."),
    fn("read_file", {"path":"auth.py"}, "def verify(t): return t.exp > now()"),
    gen("gpt-4o-mini", base_msgs, "Looks fine, no change needed."),
    fn("run_tests", {}, "FAILED: token expired"),
])

# ---- Test 2: same model, DIFFERENT PROMPT ----
msgs_a = [{"role":"system","content":SYS},{"role":"user","content":TASK}]
msgs_b = [{"role":"system","content":SYS+" Be more secure."},{"role":"user","content":TASK}]
t2_good = trace("t2-good",[
    gen("gpt-4o", msgs_a, "Reading file."),
    fn("read_file", {"path":"auth.py"}, "..."),
    fn("edit_file", {"patch":"fix expiry"}, "ok"),
    fn("run_tests", {}, "PASSED"),
])
t2_bad = trace("t2-bad",[
    gen("gpt-4o", msgs_b, "Reading file."),
    fn("read_file", {"path":"auth.py"}, "..."),
    fn("edit_file", {"patch":"fix expiry AND rotate secret"}, "error: secret store locked"),
    fn("run_tests", {}, "FAILED: cannot connect"),
])

# ---- Test 3: TOOL FAILURE (same model, same prompt) ----
t3_good = trace("t3-good",[
    gen("gpt-4o", base_msgs, "Query the DB."),
    fn("database_query", {"sql":"SELECT user_id FROM users"}, "rows: 42"),
    gen("gpt-4o", base_msgs, "Done."),
])
t3_bad = trace("t3-bad",[
    gen("gpt-4o", base_msgs, "Query the DB."),
    fn("database_query", {"sql":"SELECT * FROM users"}, "ERROR: statement timeout"),
    gen("gpt-4o", base_msgs, "Retrying."),
])

# ---- Test 4: LONG CHAIN, divergence deep at step 8 ----
def long_chain(tid, deep_arg):
    spans=[gen("gpt-4o", base_msgs, "Start.")]
    for i in range(6):
        spans.append(fn(f"step_{i}", {"i":i}, "ok"))
    spans.append(fn("charge_customer", {"customer_id":deep_arg}, "ok"))
    spans.append(gen("gpt-4o", base_msgs, "Complete."))
    return trace(tid, spans)
t4_good = long_chain("t4-good", 123)
t4_bad  = long_chain("t4-bad", 321)

for name,obj in [("t1_good",t1_good),("t1_bad",t1_bad),("t2_good",t2_good),("t2_bad",t2_bad),
                 ("t3_good",t3_good),("t3_bad",t3_bad),("t4_good",t4_good),("t4_bad",t4_bad)]:
    json.dump(obj, open(f"/home/claude/flight/{name}.json","w"))
print("traces written")

# ---- Test 5: CATEGORY B PURE — same model, same prompt, SAME tool args, different tool OUTPUT ----
t5_good = trace("t5-good",[
    gen("gpt-4o", base_msgs, "Look up the customer."),
    fn("search_customer", {"id":123}, "customer found: active"),
    gen("gpt-4o", base_msgs, "Proceeding."),
])
t5_bad = trace("t5-bad",[
    gen("gpt-4o", base_msgs, "Look up the customer."),
    fn("search_customer", {"id":123}, "ERROR: customer service unavailable"),
    gen("gpt-4o", base_msgs, "Proceeding."),
])
for name,obj in [("t5_good",t5_good),("t5_bad",t5_bad)]:
    json.dump(obj, open(f"/home/claude/flight/{name}.json","w"))
print("t5 written")
