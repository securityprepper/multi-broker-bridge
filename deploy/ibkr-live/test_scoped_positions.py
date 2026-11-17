import unittest
from types import SimpleNamespace
from decimal import Decimal
from collector import App
class Scoped(unittest.TestCase):
 def test_complete_only_matching_request(self):
  a=App();a.positionMultiEnd(999);self.assertFalse(a.pos_end.is_set())
  a.positionMultiEnd(a.position_request_id);self.assertTrue(a.pos_end.is_set())
 def test_real_position_mapping(self):
  a=App();c=SimpleNamespace(conId=1,symbol="AMAT",secType="STK",multiplier="",currency="USD")
  a.positionMulti(a.position_request_id,"U1","",c,Decimal("5"),356.20)
  self.assertEqual(a.positions[("U1",1)]["qty"],"5");self.assertEqual(a.positions[("U1",1)]["asset"],"EQUITY")
 def test_other_request_cannot_add_position(self):
  a=App();a.positionMulti(999,"U1","",None,5,1);self.assertEqual(a.positions,{})
 def test_writes_refused(self):
  a=App()
  for name in ("placeOrder","cancelOrder","reqGlobalCancel","exerciseOptions","reqAutoOpenOrders"):
   with self.assertRaisesRegex(RuntimeError,"READ_ONLY"):getattr(a,name)()
 def test_request_id_not_error_code(self):
  a=App();a.error(321,123456789,2104,"information");self.assertFalse(a.failed)
 def test_readonly_error_new_and_old_sdk(self):
  for args in ((-1,123456789,321,"Read Only"),(-1,321,"Read Only")):
   a=App();a.error(*args);self.assertTrue(a.failed);self.assertIn(321,a.error_codes)
if __name__=="__main__":unittest.main()