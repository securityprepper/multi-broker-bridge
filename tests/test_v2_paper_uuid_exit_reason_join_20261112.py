"""Offline identity, partial-fill, and reason provenance tests. No broker calls."""
import importlib.util, pathlib, unittest
p=pathlib.Path(__file__).resolve().parents[1]/"research/v2_paper_uuid_exit_reason_join_20261112.py"
spec=importlib.util.spec_from_file_location("audit",p)
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

def sample():
    a="2026-11-09T14:00:00Z";b="2026-11-09T14:05:00Z"
    trips=[{"source":"MBB","day":"2026-11-09","symbol":"MCHP",
            "entry_order_id":"MBB-ENTRY","exit_order_id":"MBB-EXIT",
            "entry_at":a,"exit_at":b,"entry":100,"exit":99.5,"qty":2}]
    orders=[
        {"id":"buy-uuid","client_order_id":"MBB-ENTRY","symbol":"MCHP",
         "status":"filled","side":"buy","filled_qty":"2","filled_avg_price":"100","filled_at":a},
        {"id":"sell-uuid","client_order_id":"MBB-EXIT","symbol":"MCHP",
         "status":"filled","side":"sell","filled_qty":"2","filled_avg_price":"99.5","filled_at":b}]
    fills=[
        {"id":"f1","order_id":"buy-uuid","qty":"2"},
        {"id":"f2","order_id":"sell-uuid","qty":"2"}]
    decisions={
       "buy-uuid":{"at":audit.dt("2026-11-09T13:59:59Z"),"reason":None,"side":"buy","symbol":"MCHP","claimed_filled":None},
       "sell-uuid":{"at":audit.dt("2026-11-09T14:04:58Z"),"reason":"profit target reached","side":"sell","symbol":"MCHP","claimed_filled":False}}
    return trips,orders,fills,decisions

class JoinTests(unittest.TestCase):
    def test_uuid_decision_join_not_just_client_prefix(self):
        r=audit.reconcile(*sample())
        self.assertEqual(r["round_trips"],1)
        self.assertEqual(r["matched_exit_decision_reason_counts"],{"profit target reached":1})
        self.assertEqual(r["matched_filled_activity_uuid_events"],2)
        self.assertEqual(r["accepted_sell_to_filled_seconds_median"],2)
    def test_partial_activities_not_multiple_round_trips(self):
        t,o,f,d=sample()
        f[1]["qty"]="1";f.append({"id":"f3","order_id":"sell-uuid","qty":"1"})
        r=audit.reconcile(t,o,f,d)
        self.assertEqual(r["round_trips"],1)
        self.assertEqual(r["matched_filled_activity_uuid_events"],3)
    def test_duplicate_fill_uuid_fails(self):
        t,o,f,d=sample();f.append(dict(f[1]))
        with self.assertRaises(ValueError):audit.reconcile(t,o,f,d)
    def test_partial_activity_quantity_mismatch_fails(self):
        t,o,f,d=sample();f[1]["qty"]="1"
        with self.assertRaisesRegex(ValueError,"quantity mismatch"):audit.reconcile(t,o,f,d)
    def test_accepted_is_not_fill(self):
        t,o,f,d=sample();o[1]["status"]="pending_new"
        with self.assertRaisesRegex(ValueError,"status/side"):audit.reconcile(t,o,f,d)
    def test_no_decision_reason_is_unknown(self):
        t,o,f,d=sample();d["sell-uuid"]["reason"]=None
        r=audit.reconcile(t,o,f,d)
        self.assertEqual(r["matched_exit_decision_reason_counts"],{"None":1})
    def test_lacking_journal_uuid_not_an_exit_cause(self):
        t,o,f,d=sample();del d["sell-uuid"]
        r=audit.reconcile(t,o,f,d)
        self.assertEqual(r["unmatched_mbb_exit_symbol_days"],[["2026-11-09","MCHP"]] if False else [("2026-11-09","MCHP")])
    def test_wrong_decision_identity_fails(self):
        t,o,f,d=sample();d["sell-uuid"]["symbol"]="AMD"
        with self.assertRaisesRegex(ValueError,"identity mismatch"):audit.reconcile(t,o,f,d)
    def test_accepted_cannot_claim_fill(self):
        t,o,f,d=sample();d["sell-uuid"]["claimed_filled"]=True
        with self.assertRaisesRegex(ValueError,"asserted fill"):audit.reconcile(t,o,f,d)
    def test_fill_time_before_journal_fails(self):
        t,o,f,d=sample();d["sell-uuid"]["at"]=audit.dt("2026-11-09T14:06:00Z")
        with self.assertRaisesRegex(ValueError,"predates"):audit.reconcile(t,o,f,d)
    def test_duplicate_paired_lot_fails(self):
        t,o,f,d=sample();t.append(dict(t[0]))
        with self.assertRaisesRegex(ValueError,"Duplicate round-trip"):audit.reconcile(t,o,f,d)
    def test_broker_verified_market_flatten_client_namespace(self):
        t,o,f,d=sample();cid='MBB-20261109-F-MCHP'
        t[0]['exit_order_id']=cid;o[1]['client_order_id']=cid;o[1]['type']='market'
        del d['sell-uuid']
        r=audit.reconcile(t,o,f,d)
        self.assertEqual(r['forced_market_fills_after_1340_ct'],[('2026-11-09','MCHP','08:05:00')])
        self.assertEqual(r['matched_exit_decision_reason_counts'],{})
    def test_not_market_cannot_claim_forced(self):
        t,o,f,d=sample();cid='MBB-20261109-F-MCHP'
        t[0]['exit_order_id']=cid;o[1]['client_order_id']=cid;o[1]['type']='limit'
        del d['sell-uuid']
        r=audit.reconcile(t,o,f,d)
        self.assertEqual(r['forced_market_fills_after_1340_ct'],[])
        self.assertEqual(r['unmatched_mbb_exit_symbol_days'],[('2026-11-09','MCHP')])
    def test_broker_retrieval_get_only_allowlist(self):
        for path in ("/v2/orders/123","/v2/orders","/v2/positions", "/v2/orders/123/cancel"):
            with self.assertRaises(ValueError):audit.get_json(path)

if __name__=="__main__":unittest.main()