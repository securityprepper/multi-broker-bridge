"""Deterministic replay of one-minute bars from NDJSON; never submits orders.

Usage:
    python -m multi_broker_bridge.replay < bars.ndjson
Every line is {"symbol":"AMD","timestamp":"2026-11-06T13:00:00Z",
"high":"450.10","low":"449.00","close":"449.80","bid":"449.70","ask":"450.00"}.
All output is advisory. One line per symbol per completed minute; evaluation
happens when an input line has {"scan_at":"..."}.
"""
import json
import sys
from datetime import datetime
from .trend import Bar,TrendMonitor

def main():
    monitor=TrendMonitor()
    seen=0
    for lineno,line in enumerate(sys.stdin,1):
        if not line.strip():continue
        data=json.loads(line)
        if "scan_at" in data:
            now=datetime.fromisoformat(str(data["scan_at"]).replace("Z","+00:00"))
            output={"scan_at":str(now),"signals":monitor.scan(now,executable_session=False),
                    "mode":"SIMULATION_NO_BROKER_ORDERS"}
            print(json.dumps(output,sort_keys=True))
            continue
        monitor.add(Bar.parse(data))
        seen+=1
    print(json.dumps({"bar_count":seen,"mode":"REPLAY_DONE_NO_ORDERS"}),file=sys.stderr)
if __name__=="__main__":
    main()
