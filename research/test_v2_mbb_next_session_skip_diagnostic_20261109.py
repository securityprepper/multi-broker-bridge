"""Research-only tests: MBB skip diagnostic never guesses absent historical fields."""
import unittest,json
from v2_mbb_next_session_skip_diagnostic_20261109 import parse_lines
DAY="2026-11-09"
def line(obj,when="03:18:41"):
    return f"2026-11-09T{when}-06:00 www3 python3[5]: "+json.dumps(obj)
class TestSkipParser(unittest.TestCase):
    def test_historical_candidate_count_cannot_prove_amd_watched(self):
        x=parse_lines([line({"status":"SCAN_COMPLETE","candidate_count":7,
          "orders":[{"symbol":"AVGO","side":"buy"},{"symbol":"INTC","side":"buy"}],
          "gate_allows_new_entries":True})],DAY)
        r=x["records"][0]
        self.assertEqual(r["stage"],"DIAGNOSTICS_MISSING")
        self.assertIsNone(r["engine_buy_watch_emitted"])
    def test_future_candidate_present_skip_exact_reason(self):
        x=parse_lines([line({"status":"SCAN_COMPLETE",
          "buy_watch_symbols":["AMD"],"skipped_buy_reasons":[
             {"symbol":"AMD","reason":"EXISTING_BROKER_POSITION"}],"orders":[]})],DAY)
        r=x["records"][0]
        self.assertEqual(r["stage"],"BUY_WATCH_SKIPPED_WITH_RECORDED_REASON")
        self.assertEqual(r["skip_reason_codes"],["EXISTING_BROKER_POSITION"])
    def test_new_watcher_absent_is_upstream_unresolved(self):
        x=parse_lines([line({"status":"SCAN_COMPLETE","buy_watch_symbols":[],
          "skipped_buy_reasons":[],"orders":[],"candidate_count":7})],DAY)
        self.assertEqual(x["records"][0]["stage"],
         "NO_BUY_WATCH_EMITTED_REASON_UPSTREAM_UNPROVEN")
    def test_watch_with_no_order_requires_reservation_reconcile(self):
        x=parse_lines([line({"status":"SCAN_COMPLETE","buy_watch_symbols":["AMD"],
          "skipped_buy_reasons":[],"orders":[]})],DAY)
        self.assertEqual(x["records"][0]["stage"],
         "BUY_WATCH_WITHOUT_SKIP_OR_ORDER_CHECK_RESERVATION_AND_BROKER")
    def test_order_status_not_fill(self):
        x=parse_lines([line({"status":"SCAN_COMPLETE","buy_watch_symbols":["AMD"],
          "skipped_buy_reasons":[],"orders":[{"symbol":"AMD","side":"buy",
          "status":"pending_new","broker_order_id":"private-id"}]})],DAY)
        self.assertEqual(x["records"][0]["stage"],
         "BUY_ORDER_REQUEST_RECORDED_BROKER_FILL_NOT_PROVEN")
        self.assertNotIn("private-id",json.dumps(x))
    def test_no_secret_cash_or_account_output(self):
        x=parse_lines([line({"status":"SCAN_COMPLETE","buy_watch_symbols":[],
          "skipped_buy_reasons":[],"orders":[],"cash":"9999.99",
          "broker_account":"ID-SECRET","APCA-API-SECRET-KEY":"SENSITIVE"})],DAY)
        self.assertNotIn("9999.99",json.dumps(x))
        self.assertNotIn("ID-SECRET",json.dumps(x))
        self.assertNotIn("SENSITIVE",json.dumps(x))
    def test_wrong_day_ignored(self):
        x=parse_lines([line({"status":"SCAN_COMPLETE"},when="03:18:41")],"2026-11-10")
        self.assertEqual(x["scans"],0)
    def test_journal_noise_ignored(self):
        x=parse_lines(["Failed as expected",line({"status":"SKIPPED"})],DAY)
        self.assertEqual(x["scans"],0)
if __name__=="__main__":unittest.main()
