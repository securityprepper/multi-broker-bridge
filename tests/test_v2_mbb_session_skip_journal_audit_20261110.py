import json
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from research.v2_mbb_session_skip_journal_audit_20261110 import summarize

TZ=ZoneInfo("America/Chicago")
def line(local_time,message):
    stamp=int(datetime.fromisoformat(local_time).timestamp()*1e6)
    return json.dumps({"__REALTIME_TIMESTAMP":str(stamp),"MESSAGE":json.dumps(message)})

def scan(watch=None,skip=None,orders=None,tracked=31):
    return {"status":"SCAN_COMPLETE","mode":"PAPER_EXECUTION",
            "buy_watch_symbols":watch or [],"skipped_buy_reasons":skip or [],
            "orders":orders or [],"tracked":tracked}

class JournalScanTests(unittest.TestCase):
    def summary(self,events):
        return summarize(events,"2026-11-10")

    def test_repeated_scans_are_events_not_unique_trades(self):
        d=self.summary([line("2026-11-10T00:20:01-06:00",scan(["AMD"])),
                        line("2026-11-10T00:20:41-06:00",scan(["AMD"]))])
        self.assertEqual(d["candidate_occurrences"],{"AMD":2})
        self.assertEqual(d["candidate_symbol_count"],1)
        self.assertEqual(d["reported_orders_not_verified_fills"],0)

    def test_prior_session_excluded(self):
        self.assertEqual(self.summary([line("2026-11-09T23:59:59-06:00",scan(["MU"]))])["scan_records"],0)

    def test_utc_to_chicago_day(self):
        d=self.summary([line("2026-11-10T00:01:00-06:00",scan(["MU"]))])
        self.assertEqual(d["scan_records"],1)

    def test_other_modes_excluded(self):
        s=scan(["MU"]);s["mode"]="DRY_RUN"
        self.assertEqual(self.summary([line("2026-11-10T01:00:00-06:00",s)])["scan_records"],0)

    def test_other_status_excluded(self):
        s=scan(["MU"]);s["status"]="SCAN_ERROR"
        self.assertEqual(self.summary([line("2026-11-10T01:00:00-06:00",s)])["scan_records"],0)

    def test_skip_counts_and_quote_reason(self):
        d=self.summary([line("2026-11-10T01:00:00-06:00",scan(["AMD","MU"],
           [{"symbol":"AMD","reason":"PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY"},
            {"symbol":"MU","reason":"NO_FRESH_BID_ASK"}]))])
        self.assertEqual(len(d["skipped_reason_occurrences"]),2)
        self.assertEqual(d["scans_with_candidates"],1)

    def test_bad_json_fails_closed(self):
        self.assertEqual(self.summary(["not json",'{"MESSAGE": "bad"}'])["scan_records"],0)

    def test_account_secrets_not_emitted(self):
        s=scan(["AMD"]);s["cash"]=500000;s["api_key"]="never_show"
        d=self.summary([line("2026-11-10T01:00:00-06:00",s)])
        self.assertNotIn("500000",json.dumps(d))
        self.assertNotIn("never_show",json.dumps(d))

    def test_order_reports_not_claimed_fills(self):
        d=self.summary([line("2026-11-10T01:00:00-06:00",scan(["AMD"],orders=[{"status":"new"}]))])
        self.assertEqual(d["reported_orders_not_verified_fills"],1)
        self.assertIn("no independent broker",d["evidence_scope"])

    def test_tracked_distribution(self):
        d=self.summary([line("2026-11-10T01:00:00-06:00",scan(tracked=31)),
                        line("2026-11-10T01:01:00-06:00",scan(tracked=31))])
        self.assertEqual(d["tracked_counts"],{31:2})

if __name__=="__main__":
    unittest.main()