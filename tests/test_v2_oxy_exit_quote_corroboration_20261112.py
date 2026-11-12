import unittest
from copy import deepcopy
from research.v2_oxy_exit_quote_corroboration_20261112 import assess, validate_fills
def fixture():
    orders=[
        {"id":"buy-uuid","symbol":"OXY","side":"buy","status":"filled","filled_at":"2026-11-12T14:48:53.801367Z","filled_qty":"34","filled_avg_price":"57.64"},
        {"id":"sell-uuid","symbol":"OXY","side":"sell","status":"filled","filled_at":"2026-11-12T15:33:50.713050Z","filled_qty":"34","filled_avg_price":"57.81"}]
    activities=[
        {"id":"act-b1","order_id":"buy-uuid","qty":"20"},
        {"id":"act-b2","order_id":"buy-uuid","qty":"14"},
        {"id":"act-s1","order_id":"sell-uuid","qty":"34"}]
    accepted={"broker_order_id":"sell-uuid","symbol":"OXY","side":"sell","at":"2026-11-12T15:33:50.068835Z","exit_signal_reason":"trailing peak reversal","exit_fill_verified":False}
    bars=[
        {"t":"2026-11-12T15:19:00Z","h":"58.175","c":"58.13"},
        {"t":"2026-11-12T15:31:00Z","h":"57.99","c":"57.94"},
        {"t":"2026-11-12T15:32:00Z","h":"57.95","c":"57.82"}]
    peak={"t":"2026-11-12T15:19:01.390202Z","bp":"58.17","ap":"58.17","bs":"200"}
    at_exit={"t":"2026-11-12T15:33:50.066255Z","bp":"57.8","ap":"57.82","bs":"200"}
    return orders,activities,accepted,bars,peak,at_exit
class ExitEvidenceTests(unittest.TestCase):
    def test_correlated_broker_activity_quote_and_completed_bar(self):
        r=assess(*fixture())
        self.assertTrue(r["corroborated"])
        self.assertEqual(r["gross_pnl_usd"],"5.78")
        self.assertEqual(r["broker_fill_activity_events"],3)
        self.assertEqual(r["first_completed_reversal_at"],"2026-11-12T15:33:00+00:00")
        self.assertFalse(r["one_pct_target_reached_by_completed_bar_high"])
    def test_partial_fill_activity_no_double_count(self):
        a=list(fixture()); a[1]=a[1][:-1]+[{"id":"act-s1","order_id":"sell-uuid","qty":"20"},{"id":"act-s2","order_id":"sell-uuid","qty":"14"}]
        self.assertEqual(assess(*a)["gross_pnl_usd"],"5.78")
    def test_missing_fills_refused(self):
        a=list(fixture());a[1]=a[1][:-1]
        with self.assertRaises(ValueError):assess(*a)
    def test_duplicate_activity_uuid_refused(self):
        a=list(fixture());a[1][1]["id"]="act-b1"
        with self.assertRaises(ValueError):assess(*a)
    def test_journal_uuid_mismatch_refused(self):
        a=list(fixture());a[2]["broker_order_id"]="another"
        with self.assertRaises(ValueError):assess(*a)
    def test_acceptance_not_a_fill(self):
        a=list(fixture());a[2]["exit_fill_verified"]=True
        with self.assertRaises(ValueError):assess(*a)
    def test_incomplete_current_minute_not_allowed(self):
        a=list(fixture());a[3][-1]["t"]="2026-11-12T15:33:00Z"
        self.assertFalse(assess(*a)["corroborated"])
    def test_future_quote_refused(self):
        a=list(fixture());a[5]["t"]="2026-11-12T15:33:50.100000Z"
        with self.assertRaises(ValueError):assess(*a)
    def test_stale_quote_refused(self):
        a=list(fixture());a[5]["t"]="2026-11-12T15:33:48.000000Z"
        with self.assertRaises(ValueError):assess(*a)
    def test_crossed_quote_refused(self):
        a=list(fixture());a[5]["ap"]="57.79"
        with self.assertRaises(ValueError):assess(*a)
    def test_undersized_quote_refused(self):
        a=list(fixture());a[4]["bs"]="1"
        with self.assertRaises(ValueError):assess(*a)
    def test_target_not_inferred_from_exit_fill(self):
        r=assess(*fixture())
        self.assertFalse(r["one_pct_target_reached_by_completed_bar_high"])
        self.assertEqual(r["accepted_reason"],"trailing peak reversal")
if __name__=="__main__":unittest.main()
