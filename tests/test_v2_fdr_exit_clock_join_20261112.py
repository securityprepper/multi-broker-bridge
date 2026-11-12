import importlib.util,unittest,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
s=importlib.util.spec_from_file_location("fdr",str(Path(__file__).resolve().parents[1] / "research" / "v2_fdr_exit_clock_join_20261112.py"))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def trade(symbol="AMD",exit_at="2026-11-09T13:30:14Z",src="FDR"):
    return {"source":src,"day":"2026-11-09","symbol":symbol,
       "entry_at":"2026-11-09T13:06:14Z","exit_at":exit_at,"entry":"469",
       "exit":"464.52","qty":4,"entry_type":"limit","exit_type":"limit",
       "entry_order_id":"entry-"+symbol,"exit_order_id":"exit-"+symbol}
def log(kind="PREOPEN_EXIT_REQUEST",symbol="AMD",micros=1794223812000000):
    return json.dumps({"__REALTIME_TIMESTAMP":str(micros),
       "MESSAGE":json.dumps({"strategy":"five_day_rebound","status":"EXIT_MANAGEMENT",
                             "orders":[kind+":"+symbol]})})
class FdrJoin(unittest.TestCase):
    def test_parse_and_causal_fill_join(self):
        at=datetime(2026,11,9,13,30,12,tzinfo=timezone.utc)
        l=log(micros=int(at.timestamp()*1e6))
        out=m.reconcile([trade()],m.read_exit_journal([l]))
        self.assertEqual(out["scheduled_exit_identified"],1)
        self.assertEqual(out["gross_filled_pnl_usd"],"-17.92")
        self.assertEqual(out["unknown_exit_origin"],0)
    def test_no_journal_not_proven(self):
        self.assertEqual(m.reconcile([trade()],[])["unknown_exit_origin"],1)
    def test_quote_skip_not_a_sell(self):
        at=datetime(2026,11,9,13,30,12,tzinfo=timezone.utc)
        events=m.read_exit_journal([log("NO_FRESH_EXIT_QUOTE",micros=int(at.timestamp()*1e6))])
        self.assertEqual(m.reconcile([trade()],events)["scheduled_exit_identified"],0)
    def test_fill_preceding_request_unmatched(self):
        at=datetime(2026,11,9,13,32,12,tzinfo=timezone.utc)
        events=m.read_exit_journal([log(micros=int(at.timestamp()*1e6))])
        self.assertEqual(m.reconcile([trade()],events)["unknown_exit_origin"],1)
    def test_duplicate_pair_rejected(self):
        with self.assertRaises(ValueError):m.reconcile([trade(),trade()],[])
    def test_nonfilled_or_missing_fields_fail_closed(self):
        t=trade();t["exit_order_id"]=""
        with self.assertRaises(ValueError):m.reconcile([t],[])
    def test_other_sources_omitted(self):
        self.assertEqual(m.reconcile([trade(src="MBB")],[])["roundtrips"],0)
    def test_different_symbol_not_match(self):
        at=datetime(2026,11,9,13,30,12,tzinfo=timezone.utc)
        events=m.read_exit_journal([log(symbol="MU",micros=int(at.timestamp()*1e6))])
        self.assertEqual(m.reconcile([trade()],events)["scheduled_exit_identified"],0)
if __name__=="__main__":unittest.main()