"""No-secret journal aggregation tests."""
import datetime
import json
import unittest
from research import v2_auto_paper_scan_reason_audit_20261111 as a

def record(at, report, account_id="SECRET_ACCOUNT", cash="SECRET_CASH"):
    payload={"__REALTIME_TIMESTAMP":str(int(datetime.datetime.fromisoformat(at).timestamp()*1e6)),
             "MESSAGE":json.dumps({"status":"SCAN_COMPLETE", "account_id":account_id,
                                   "cash":cash, **report})}
    return json.dumps(payload)

class TestJournalReasonAudit(unittest.TestCase):
    def test_categories_by_chicago_day_and_no_secrets(self):
        first=record("2026-11-11T05:59:59+00:00",{
            "candidate_count":2,"buy_watch_symbols":["AMD","MU"],
            "orders":[{"client_order_id":"PRIVATE_CLIENT"}],
            "skipped_buy_reasons":[{"symbol":"AMD","reason":"NO_FRESH_BID_ASK"},
                                   {"symbol":"MU","reason":"NEVER_SEEN_SECRET_REASON"}]
        })
        second=record("2026-11-11T06:00:01+00:00",{
            "candidate_count":1,"buy_watch_symbols":["MU"],"orders":[],
            "skipped_buy_reasons":[{"symbol":"MU","reason":"PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY"}]
        })
        obj=a.aggregate([first,second])
        self.assertEqual(obj["2026-11-10"]["scans"],1)
        self.assertEqual(obj["2026-11-11"]["scans"],1)
        self.assertEqual(obj["2026-11-10"]["skip_reason_NO_FRESH_BID_ASK"],1)
        self.assertEqual(obj["2026-11-10"]["skip_reason_OTHER_UNRECOGNIZED"],1)
        self.assertEqual(obj["2026-11-11"]["skip_reason_PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY"],1)
        raw=json.dumps(obj)
        for banned in ("SECRET_ACCOUNT","SECRET_CASH","PRIVATE_CLIENT","AMD","MU","NEVER_SEEN_SECRET_REASON"):
            self.assertNotIn(banned,raw)
    def test_nonjson_and_non_scan_ignored(self):
        obj=a.aggregate(["notjson",json.dumps({"MESSAGE":"{}","__REALTIME_TIMESTAMP":"1"}),
                         json.dumps({"MESSAGE":json.dumps({"status":"NOOP"}),"__REALTIME_TIMESTAMP":"1790000000000000"})])
        self.assertEqual(obj,{})
    def test_rejects_malformed_candidates(self):
        r=record("2026-11-11T18:00:00+00:00",{
            "candidate_count":-1,"buy_watch_symbols":[],"orders":[],"skipped_buy_reasons":[]})
        self.assertIsNone(a.parse_journal(r))
    def test_counts_appearances_not_fills(self):
        r=record("2026-11-11T18:00:00+00:00",{
            "candidate_count":3,"buy_watch_symbols":["AMD","AMD","MU"],"orders":[{},{}],
            "skipped_buy_reasons":[{"reason":"NO_FRESH_BID_ASK"},
                                   {"reason":"NO_FRESH_BID_ASK"}]})
        o=a.aggregate([r])["2026-11-11"]
        self.assertEqual(o["buy_watch_symbol_appearances"],3)
        self.assertEqual(o["skip_reason_NO_FRESH_BID_ASK"],2)
        self.assertEqual(o["scans_with_quote_skip"],1)
        self.assertEqual(o["reported_order_objects_not_fills"],2)

if __name__=="__main__":
    unittest.main()