"""R1M mandatory-session-flat expiration bug: source AST, offline only."""
from pathlib import Path
import ast
import datetime as dt
from zoneinfo import ZoneInfo

P=Path('/opt/securityprepper/direction-paper-executor/one_minute_research.py')
t=ast.parse(P.read_text())
f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='manage_research_exits')
nodes=[n.value for n in ast.walk(f) if isinstance(n,ast.Assign)
       and any(isinstance(k,ast.Name) and k.id=='latest' for k in n.targets)]
assert len(nodes)==1
present=compile(ast.Expression(nodes[0]),str(P),'eval')
print('R1M_CURRENT_FLAT',ast.unparse(nodes[0]))
tz=ZoneInfo('America/Chicago')
entry=dt.datetime(2026,11,18,11,0,tzinfo=tz)
deadline=entry.replace(hour=13,minute=40,second=0,microsecond=0)
tests=[
 (18,13,39,False),
 (18,13,40,True),
 (18,23,59,True),
 (19,0,0,True),
 (19,3,5,True),
 (19,13,39,True),
 (19,13,40,True),
 (20,23,59,True),
 (21,3,0,True)
]
bugs=[]
for day,hour,minute,expected in tests:
    local=entry.replace(day=day,hour=hour,minute=minute)
    got=bool(eval(present,{'local':local}))
    corrected=(local>=deadline)
    assert corrected==expected
    if got!=expected:bugs.append((local.isoformat(),got,expected))
print('TEST_COUNT',len(tests),'CURRENT_BUG_COUNT',len(bugs))
print('BUGS',bugs)
assert len(bugs)==4
print('NO_BROKER_ACCESS')
