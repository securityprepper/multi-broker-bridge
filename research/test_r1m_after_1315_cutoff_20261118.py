"""Offline regression for R1M PAPER last-entry window. No broker access.

This test checks the *exact installed* research_open conditional rather than
a retyped version, then shows the source-only corrective predicate.
"""
import ast
import datetime as dt
from zoneinfo import ZoneInfo
from pathlib import Path

SOURCE = Path("/opt/securityprepper/direction-paper-executor/one_minute_research.py")
tree = ast.parse(SOURCE.read_text())
fn = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="research_open")
checks = [n for n in ast.walk(fn) if isinstance(n,ast.If) and any(
    isinstance(x,ast.Constant) and x.value=="RESEARCH_ENTRY_CUTOFF_BEFORE_MANDATORY_2PM_FLAT"
    for x in ast.walk(n))]
assert len(checks)==1
guard = checks[0].test
expression = ast.unparse(guard)
assert "local.weekday()" in expression and "< 19" in expression
installed = compile(ast.Expression(guard),str(SOURCE),"eval")
# 04:00 ET is 03:00 CT, so earlier BOATS is excluded. No entries
# after the same day's 13:15 CT (including the 19:00 CT BOATS reset).
fixed_text = "(local.weekday()>=5 or local.time()<dt.time(3,0) or local.time()>=dt.time(13,15))"
fixed = compile(fixed_text, "RESEARCH_ONLY_FIX", "eval")
tests=[
("2026-11-18T02:59:00-06:00",True),
("2026-11-18T03:00:00-06:00",False),
("2026-11-18T13:14:00-06:00",False),
("2026-11-18T13:15:00-06:00",True),
("2026-11-18T18:59:00-06:00",True),
("2026-11-18T19:00:00-06:00",True),
("2026-11-18T19:30:00-06:00",True),
("2026-11-18T23:00:00-06:00",True),
("2026-11-19T00:00:00-06:00",True),
("2026-11-19T02:59:00-06:00",True),
("2026-11-19T03:00:00-06:00",False),
("2026-11-21T05:00:00-06:00",True)
]
bad=[]
for date,want_block in tests:
 local=dt.datetime.fromisoformat(date).astimezone(ZoneInfo("America/Chicago"))
 current=eval(installed,{"local":local})
 corrected=eval(fixed,{"local":local,"dt":dt})
 assert corrected is want_block,(date,corrected,want_block)
 if current != want_block:
    bad.append((date,current,want_block))
print("EXACT_INSTALLED_GUARD",expression)
print("CORRECTED_GUARD",fixed_text)
print("ISOLATED_TEST_CASES",len(tests))
print("INSTALLED_POLICY_VIOLATION_CASES",len(bad),bad)
print("CORRECTED_POLICY_VIOLATION_CASES",0)
assert len(bad)>=5
print("OFFLINE_REGRESSION_PASSED_TRUE_BUG_CONFIRMED")
