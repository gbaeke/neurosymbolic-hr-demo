"""Neurosymbolic HR demo: LLM (neural) extracts facts -> clingo (symbolic) decides.

    python hr_demo.py            # uses Claude if ANTHROPIC_API_KEY is set
    python hr_demo.py --gateway  # uses the local agentgateway (localhost:4000)
    python hr_demo.py --offline  # uses canned extractions, no API needed
"""

import sys
from typing import Literal

import clingo
from pydantic import BaseModel

# Free-text leave requests, as an employee would type them.
# The HR system supplies what it knows (tenure, days used); the email supplies the rest.
REQUESTS = [
    ("anna",  "Hi! I'd like to take 5 days off in the second week of July for my sister's wedding. Thanks, Anna (Marketing)"),
    ("bram",  "Hey HR, Bram from Finance here. Planning a ski trip, 7 days in December please."),
    ("chloe", "Hello, I started in March and would love to take 4 days off in May to move house. - Chloé, Engineering"),
    ("dirk",  "Dirk here (Sales). Taking my long-planned trip to Japan: 15 days in October."),
]

HR_SYSTEM = {  # what the HR database already knows
    "anna":  {"tenure_months": 40,  "days_used": 8,  "contract": "employee"},
    "bram":  {"tenure_months": 130, "days_used": 3,  "contract": "employee"},
    "chloe": {"tenure_months": 4,   "days_used": 0,  "contract": "employee"},
    "dirk":  {"tenure_months": 75,  "days_used": 6,  "contract": "employee"},
}


class LeaveRequest(BaseModel):
    department: Literal["marketing", "finance", "engineering", "sales", "hr", "other"]
    month: int  # 1-12
    days: int


# --- Step 1: NEURAL. Turn messy text into structured facts. -------------------
def extract_with_llm(text: str) -> LeaveRequest:
    import anthropic

    if "--gateway" in sys.argv:  # local agentgateway on :4000, no API key needed
        client = anthropic.Anthropic(base_url="http://localhost:4000", api_key="unused")
        model = "gpt-6-luna"
    else:
        client = anthropic.Anthropic()
        model = "claude-opus-5-5"

    response = client.messages.parse(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": f"Extract the leave request details from this message:\n\n{text}"}],
        output_format=LeaveRequest,
    )
    return response.parsed_output


OFFLINE = {  # what Claude would return, so the demo runs without an API key
    "anna":  LeaveRequest(department="marketing",   month=7,  days=5),
    "bram":  LeaveRequest(department="finance",     month=12, days=7),
    "chloe": LeaveRequest(department="engineering", month=5,  days=4),
    "dirk":  LeaveRequest(department="sales",       month=10, days=15),
}


# --- Step 2: bridge. Structured data -> ASP facts. ----------------------------
def to_facts(emp: str, req: LeaveRequest) -> str:
    hr = HR_SYSTEM[emp]
    return "\n".join([
        f"tenure_months({emp}, {hr['tenure_months']}).",
        f"days_used({emp}, {hr['days_used']}).",
        f"contract({emp}, {hr['contract']}).",
        f"department({emp}, {req.department}).",
        f"request({emp}, {req.month}, {req.days}).",
    ])


# --- Step 3: SYMBOLIC. Clingo applies the policy deterministically. ----------
def decide(facts: str) -> dict:
    ctl = clingo.Control()
    ctl.load("hr_rules.lp")
    ctl.add("base", [], facts)
    ctl.ground([("base", [])])

    result = {"violations": [], "approvals": []}
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            for atom in model.symbols(shown=True):
                arg = str(atom.arguments[1])
                if atom.name == "decision":
                    result["decision"] = arg
                elif atom.name == "violation":
                    result["violations"].append(arg)
                elif atom.name == "needs_approval":
                    result["approvals"].append(arg)
                elif atom.name == "remaining":
                    result["remaining"] = int(arg)
    return result


def main():
    offline = "--offline" in sys.argv
    for emp, text in REQUESTS:
        req = OFFLINE[emp] if offline else extract_with_llm(text)
        facts = to_facts(emp, req)
        result = decide(facts)

        print(f"\n📨 {text}")
        print(f"   🧠 extracted: {req.model_dump()}")
        print(f"   ⚖️  {result['decision'].upper()}  (balance left: {result['remaining']} days)")
        for v in result["violations"]:
            print(f"      ✗ {v}")
        for a in result["approvals"]:
            print(f"      ⚠ {a}")


if __name__ == "__main__":
    main()
