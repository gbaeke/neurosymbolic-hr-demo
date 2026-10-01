# Neurosymbolic HR demo

A small demo of **neurosymbolic AI**: an LLM reads messy, free-text leave requests, and a logic solver applies the company's leave policy to them. The LLM never decides anything.

## Why neurosymbolic?

LLMs are very good at understanding language, such as "the second week of July" or "Bram from Finance here". They are bad at reliably following rules: they can miscount, skip a rule or give different answers to the same question. For decisions with consequences, like approving leave, you want the rules applied exactly, the same way every time, with a clear reason.

So this demo splits the work:

| Part | Good at | In this demo |
|---|---|---|
| **Neural** (LLM, here Claude) | Understanding unstructured text | Turns an email into `{department, month, days}` |
| **Symbolic** (clingo, a logic solver) | Exact, explainable rule application | Applies the HR policy and returns a decision plus the reasons |

Each part does what it's good at. If a decision is wrong, you can check whether the LLM extracted the wrong facts or the policy itself is wrong.

## How it works

```
"Hey HR, Bram from Finance here.        ┌──────────┐   department=finance   ┌─────────────┐
 Planning a ski trip, 7 days in   ───▶  │   LLM    │ ─▶ month=12        ─▶  │   clingo    │ ─▶ REJECTED
 December please."                      │ (neural) │    days=7              │ (symbolic)  │    finance_december_freeze
                                        └──────────┘          ▲             └─────────────┘
                                                              │                    ▲
                                              HR database: tenure, days used       │
                                                                             hr_rules.lp
```

1. **Extract (neural).** The LLM receives the email and must return data matching a fixed schema (a Pydantic model). It can't produce free-form answers, only the fields the system needs.
2. **Bridge.** The extracted fields are combined with what the HR database already knows (tenure, days used, contract type) and written out as logic facts, e.g. `request(bram, 12, 7).`
3. **Decide (symbolic).** clingo loads the policy from `hr_rules.lp`, combines it with the facts and derives the decision along with every rule that fired.

## What is clingo / ASP?

[clingo](https://potassco.org/clingo/) is a solver for **Answer Set Programming (ASP)**, a declarative logic language. Instead of writing step-by-step code, you write rules of the form "this is true **if** these are true". A rule reads right to left:

```prolog
violation(E, finance_december_freeze) :- request(E, 12, _), department(E, finance).
```

> *Employee E has a `finance_december_freeze` violation **if** E requests leave in month 12 **and** E works in finance.*

`_` means "any value", and `not` means "cannot be shown to be true". The solver works out everything that follows from the facts and rules. Because the policy is just a list of rules, an HR person can read it, and changing the policy means editing one line, not the code.

## The policy (`hr_rules.lp`)

- **Entitlement:** 20 days, plus 1 extra day per 5 full years of service.
- **Hard rules** (any one means **rejected**):
  - not enough remaining days
  - in the first 6 months (probation), max 2 days at a time
  - Finance can't take leave in December (year-end close)
- **Soft rules** (allowed, but needs **manager approval**):
  - more than 10 days in one request
  - the requester is a contractor
- Otherwise: **approved**.

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python hr_demo.py --offline  # canned extractions, no API key needed (start here)
python hr_demo.py            # real extraction with Claude; requires ANTHROPIC_API_KEY
python hr_demo.py --gateway  # uses a local agentgateway at localhost:4000
```

Expected output (`--offline`):

```
📨 Hi! I'd like to take 5 days off in the second week of July for my sister's wedding. Thanks, Anna (Marketing)
   🧠 extracted: {'department': 'marketing', 'month': 7, 'days': 5}
   ⚖️  APPROVED  (balance left: 12 days)

📨 Hey HR, Bram from Finance here. Planning a ski trip, 7 days in December please.
   🧠 extracted: {'department': 'finance', 'month': 12, 'days': 7}
   ⚖️  REJECTED  (balance left: 19 days)
      ✗ finance_december_freeze

📨 Hello, I started in March and would love to take 4 days off in May to move house. - Chloé, Engineering
   🧠 extracted: {'department': 'engineering', 'month': 5, 'days': 4}
   ⚖️  REJECTED  (balance left: 20 days)
      ✗ probation_max_2_days

📨 Dirk here (Sales). Taking my long-planned trip to Japan: 15 days in October.
   🧠 extracted: {'department': 'sales', 'month': 10, 'days': 15}
   ⚖️  MANAGER_APPROVAL  (balance left: 15 days)
      ⚠ more_than_10_days
```

"Balance left" is the employee's balance *before* this request.

## Try it yourself

- **Change the policy:** edit `hr_rules.lp`, for example remove the December freeze or raise the 10-day threshold, and run again. The Python code stays the same.
- **Add a request:** add an entry to `REQUESTS` and `HR_SYSTEM` in `hr_demo.py`. Add it to `OFFLINE` too if you want it to work in `--offline` mode.
- **Test the LLM:** write a vague or tricky email and see whether the extraction holds up.

## Files

- `hr_demo.py`: the pipeline (LLM extraction → logic facts → clingo decision) and the sample data
- `hr_rules.lp`: the leave policy as ASP rules
- `requirements.txt`: Python dependencies
