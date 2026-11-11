"""Pure offline no-order versus unknown post-reservation outcomes."""
import unittest
from research.v2_receiving_broker_no_post_resolution_20261111 import resolution, ALLOWED_VETO
BASE={"intent_status":"RESERVED_UNKNOWN","reservation_lock_owned":True,
      "exclusive_writer_proven":True,"broker_post_started":False,
      "veto_code":"ENTRY_CUTOFF_PASSED",
      "client_order_id":"sp-paper-recommendation-123"}

class PostReservationVetoTests(unittest.TestCase):
    def outcome(self,**kw):
        return resolution(**dict(BASE,**kw))
    def test_cutoff_veto_terminal_without_resubmission(self):
        x=self.outcome()
        self.assertEqual(x["proposed_status"],"PRE_SUBMIT_NO_ORDER")
        self.assertFalse(x["post_permitted"])
        self.assertFalse(x["automatic_retry_permitted"])
        self.assertTrue(x["retain_same_broker_claim"])
        self.assertFalse(x["requires_broker_readback"])
    def test_each_hard_gate_no_post_veto(self):
        for code in ALLOWED_VETO:
            with self.subTest(code=code):
                self.assertEqual(self.outcome(veto_code=code)["proposed_status"],"PRE_SUBMIT_NO_ORDER")
    def test_hypothetical_or_actual_post_started_needs_readback(self):
        for state in (True,None,0,"False"):
            with self.subTest(state=state):
                x=self.outcome(broker_post_started=state)
                self.assertEqual(x["proposed_status"],"RESERVED_UNKNOWN")
                self.assertTrue(x["requires_broker_readback"])
    def test_missing_or_ambiguous_lock_cannot_claim_no_post(self):
        for state in (False,None,0):
            with self.subTest(state=state):
                self.assertEqual(self.outcome(reservation_lock_owned=state)["proposed_status"],"RESERVED_UNKNOWN")
                self.assertEqual(self.outcome(exclusive_writer_proven=state)["proposed_status"],"RESERVED_UNKNOWN")
    def test_wrong_row_state_not_reclassified_as_no_order(self):
        for status in ("PENDING","BROKER_ACCEPTED","BROKER_REJECTED","REBOUND_ORDER_READY"):
            self.assertEqual(self.outcome(intent_status=status)["proposed_status"],"RESERVED_UNKNOWN")
    def test_unrecognized_reason_not_authoritative(self):
        for reason in ("",None,"POST_TIMEOUT","BROKER_REJECTED","RETRY_NOW"):
            self.assertEqual(self.outcome(veto_code=reason)["proposed_status"],"RESERVED_UNKNOWN")
    def test_bad_client_id_cannot_link_receipt(self):
        for cid in ("",None,"invalid id","/orders/123"):
            self.assertEqual(self.outcome(client_order_id=cid)["proposed_status"],"RESERVED_UNKNOWN")
    def test_never_claims_broker_order_verification_or_reentry(self):
        for state in (False,True,None):
            x=self.outcome(broker_post_started=state)
            self.assertFalse(x["broker_order_verified"])
            self.assertFalse(x["automatic_retry_permitted"])
            self.assertTrue(x["retain_same_broker_claim"])

if __name__=="__main__":unittest.main()
