"""Full sealed-before-outcome prospective test on synthetic Nov 12 (NEVER historical relabel)."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from research import v2_forward_only_sector_shadow_20261109 as f
from research import v2_forward_shadow_score_20261111 as scoring

ET=ZoneInfo("America/New_York")
NOW=datetime(2026,11,12,9,35,40,tzinfo=ET)
PREVIOUS=["2026-11-05","2026-11-06","2026-11-09","2026-11-10","2026-11-11"]

def market(which):
    if which=="1Day":
        return {s:[{"t":d+"T05:00:00Z","c":100.0} for d in PREVIOUS] for s in f.symbols()}
    result={}
    for s in f.symbols():
        # Three leading peers and their ETF all rise, other sector constituents too.
        result[s]=[
            {"t":"2026-11-12T14:25:00Z","o":100,"h":100,"l":100,"c":100},
            {"t":"2026-11-12T14:30:00Z","o":100,"h":100.4,"l":100,"c":100.4},
        ]
    return result

class EndToEndShadowTests(unittest.TestCase):
    def test_immutable_first_seen_forecast_then_future_only_score(self):
        with tempfile.TemporaryDirectory() as td,patch.dict(
            "os.environ",{"V2_SHADOW_STATE_ROOT":td}):
            def fake(n,frame,creds):
                return market(frame)
            r=f.run(NOW,holiday_check=lambda _:True,fetch=fake)
            self.assertEqual(r["status"],"RESEARCH_SHADOW_SEALED")
            self.assertEqual(r["benchmark_forecasts_issued"],7)
            self.assertEqual(r["peer_forecasts_issued"],7)
            path=Path(td)/"2026-11-12"/"0935.json"
            original=path.read_bytes()
            saved=scoring.validate_seal(original,"2026-11-12","09:35")
            self.assertEqual(set(saved["sectors"]),set(f.SECTORS))
            self.assertEqual(saved["orders_submitted"],0)
            self.assertFalse(saved["PAPER_orders_allowed"])
            self.assertFalse(saved["LIVE_orders_allowed"])
            self.assertNotIn("future_mark", original.decode())
            self.assertEqual(f.run(NOW,holiday_check=lambda _:True,fetch=
                lambda *args: (_ for _ in ()).throw(AssertionError("fetched twice")))["status"],"ALREADY_SEALED")
            future={}
            for sector,(etf,_) in f.SECTORS.items():
                future[etf]={
                    "2026-11-12 10:35":{
                        "close":101.0,"bar_available_after_ET":"2026-11-12T10:40:00-05:00"
                    },
                    "2026-11-12 14:35":{
                        "close":99.8,"bar_available_after_ET":"2026-11-12T14:40:00-05:00"
                    },
                }
            import hashlib
            rows,summary=scoring.evaluate_seals("2026-11-12",{"09:35":(saved,hashlib.sha256(original).hexdigest())},future)
            self.assertEqual(len([x for x in rows if x.get("sector")]),28)
            self.assertEqual(sum(summary[s]["benchmark_side"]["60m"]["hits"] for s in f.SECTORS),7)
            self.assertEqual(sum(summary[s]["benchmark_side"]["flat"]["misses"] for s in f.SECTORS),7)
            self.assertEqual(original,path.read_bytes())
    def test_stop_before_holiday_and_no_market_calls(self):
        r=scoring.run(datetime(2026,11,12,14,50,tzinfo=ET),
            holiday_check=lambda _:False,
            fetch=lambda *args: (_ for _ in ()).throw(AssertionError("called")))
        self.assertEqual(r["market_data_requests"],0)
        self.assertEqual(r["status"],"HOLIDAY_PAUSED_NO_SCORE_OR_POLL")
if __name__=="__main__":
    unittest.main()
