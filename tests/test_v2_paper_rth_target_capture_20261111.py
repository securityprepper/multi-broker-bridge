"""Offline target audit tests: never pretend high/low crossing proves an order fill."""
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

CT=ZoneInfo("America/Chicago")
SCRIPT=Path(__file__).resolve().parents[1]/"research"/"v2_paper_rth_target_capture_20261111.py"

def fixture(omit=False):
    entry=datetime(2026,11,11,13,35,30,tzinfo=CT)
    exit_=datetime(2026,11,11,13,35,50,tzinfo=CT)
    bars=[]
    for minute in (36,37,38,39):
        if omit and minute==38:continue
        dt=datetime(2026,11,11,13,minute,0,tzinfo=CT)
        # First completed after-entry bar crosses both 1% profit and 1% stop.
        high=101.1 if minute==36 else 100.1
        low=98.9 if minute==36 else 99.7
        bars.append({"t":dt.isoformat(),"o":100,"h":high,"l":low,"c":99.9,"v":10})
    raw={"research_only":True,"broker_orders_submitted":0,
         "trades":[{"source":"MBB","day":"2026-11-11","symbol":"FAKE",
            "entry_at":entry.isoformat(),"exit_at":exit_.isoformat(),
            "entry":100,"exit":99.8,"qty":1,"entry_type":"limit","exit_type":"limit"}],
         "bars":{"2026-11-11|FAKE":bars}}
    quotes={"quotes":{"2026-11-11|FAKE":{"status":"FRESH_TIGHT_INDICATIVE_QUOTE",
             "bid":99.8,"ask":99.9,"bid_size":10}}}
    return raw,quotes

def execute(omit=False):
    raw,quotes=fixture(omit)
    with tempfile.TemporaryDirectory() as td:
        a=Path(td)/"fills.json";b=Path(td)/"quotes.json"
        a.write_text(json.dumps(raw));b.write_text(json.dumps(quotes))
        r=subprocess.run([sys.executable,str(SCRIPT),"--fills",str(a),
                          "--flat-quotes",str(b)],capture_output=True,text=True,check=True)
        return r.stdout

class TestRthTargetAudit(unittest.TestCase):
    def test_high_and_low_same_bar_favors_stop_conservatively(self):
        s=execute()
        self.assertIn("FULLPATH_HIT 1 / 1",s)
        self.assertIn("tgt 1.0 stop_first 1 target_touch 0",s)
    def test_missing_minute_is_excluded_from_model(self):
        s=execute(omit=True)
        self.assertIn("full 0",s)
        self.assertIn("FULLPATH_HIT 0 / 0",s)
    def test_only_local_no_broker_interface(self):
        s=SCRIPT.read_text()
        self.assertNotIn("urllib.request",s)
        self.assertNotIn("paper_api(",s)
        self.assertNotIn("POST",s)
if __name__=="__main__":unittest.main()
