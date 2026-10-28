# Reflection: Build Your First Agent Loop

**Name:** _your name_  **Date:** _date_  **Model used:** _e.g. openai/gpt-oss-120b on Groq_

> Write in your own words. Be specific: quote what *your* runs showed. Vague answers will be sent back.

---

## Pause-and-observe answers

**#1. Why does a `tool` message carry `tool_call_id`?**

_your answer_

**#2. Where does the customer's identity come from, and what breaks if `customer_id` were a tool argument?**

_your answer_

**#3. Why do "order does not exist" and "belongs to someone else" return the same error?**

_your answer_

**#4. Why are refund rules in code instead of the prompt? Name two failure modes.**

_your answer_

**#5. Why restrict `reason` with an allowed-values list? What does your code do with an unlisted reason?**

_your answer_

**#6. Errors are returned as data. Who reads them, and what happens on the next lap?**

_your answer_

**#7. What does a green `check_my_work.py` prove, and what does it not prove?**

_your answer_

---

## Part 6: Live scenarios

Fill in **what the model actually did**. Run each at least once (B three times).

| Scenario | My prediction (before running) | Tool sequence the model chose | Steps / tokens | Reply correct? (check vs DB) | Path reasonable? Notes |
|---|---|---|---|---|---|
| A | | | | | |
| B (run 1) | | | | | |
| B (run 2) | | | | | |
| B (run 3) | | | | | |
| C | | | | | |
| D | | | | | |
| E | | | | | |
| F | | | | | |
| G | | | | | |

**#8. Was scenario B identical across the 3 runs? What does that mean for testing agents?**

_your answer_

**#9. Scenario G: what happened, and why is a prompt rule weaker than a route with no tools?**

_your answer_

---

## Part 7: Experiments

| # | What I changed | What happened (status, steps, reply, tool calls) | What it taught me |
|---|---|---|---|
| E1 | `MAX_STEPS = 2` | | |
| E2 | description of `check_refund_eligibility` = `"eligibility"` | | |
| E3 | removed "Never guess..." rule | | |
| E4 | removed "ONE tool at a time" rule | | |
| E5 | `TOKEN_BUDGET = 1500` | | |
| E6 | ownership check removed (reverted!) | | |

---

## Part 8: Reflection questions

**1. The one-question test (slide 8): is my agent really an agent? What would I replace with plain code if cost and predictability mattered most?**

_your answer_

**2. Scenario C step by step: who decided each step, the model or the code?**

_your answer_

**3. Why is returning `{"error": ...}` from `execute_tool` better than raising? One concrete example from my runs.**

_your answer_

**4. Why must the stop check run every lap, and why in code rather than in the prompt?**

_your answer_

**5. Which of `send_email`, `issue_refund`, `list_orders`, `create_replacement` would I put behind human approval, and why?**

_your answer_

**6. The hardest bug I hit, how I found it, and what the trace showed me.**

_your answer_

**7. AI use: where did an AI tool (or documentation) help me, and where was it wrong or misleading? One concrete example, and how I caught it.**

_your answer_

---

*Don’t focus on getting the answer. Focus on learning how to engineer the solution.*
