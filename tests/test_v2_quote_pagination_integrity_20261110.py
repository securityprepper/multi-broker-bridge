import unittest
from datetime import datetime,timezone
from research.v2_quote_pagination_integrity_20261110 import audit_pages,requires_more_pages
T=datetime(2026,11,10,14,46,46,tzinfo=timezone.utc)
Q={"t":"2026-11-10T14:46:45.780Z","bp":100,"ap":100.05}
class TestQuotePagination(unittest.TestCase):
 def test_incomplete_page_not_absent(self):
  x=audit_pages(["AMD","MU"],[{"quotes":{"AMD":[Q]},"next_page_token":"p2"}],T)
  self.assertEqual(x["symbol_reasons"]["MU"],"NOT_YET_FETCHED_PAGE")
  self.assertTrue(requires_more_pages(x))
 def test_completed_page_absent(self):
  x=audit_pages(["AMD","MU"],[{"quotes":{"AMD":[Q]},"next_page_token":None}],T)
  self.assertEqual(x["symbol_reasons"]["MU"],"NO_QUOTE_IN_COMPLETE_WINDOW")
 def test_later_page_recovers_quote(self):
  x=audit_pages(["AMD","MU"],[{"quotes":{"AMD":[Q]},"next_page_token":"p2"},
      {"quotes":{"MU":[Q]},"next_page_token":None}],T)
  self.assertEqual(x["reason_counts"],{"ACCEPT":2})
 def test_crossed_quote(self):
  q={**Q,"bp":101}
  x=audit_pages(["AMD"],[{"quotes":{"AMD":[q]}}],T)
  self.assertEqual(x["symbol_reasons"]["AMD"],"CROSSED")
 def test_stale(self):
  q={**Q,"t":"2026-11-10T14:40:00Z"}
  x=audit_pages(["AMD"],[{"quotes":{"AMD":[q]}}],T)
  self.assertEqual(x["symbol_reasons"]["AMD"],"STALE")
 def test_wide(self):
  q={**Q,"ap":105}
  x=audit_pages(["AMD"],[{"quotes":{"AMD":[q]}}],T)
  self.assertEqual(x["symbol_reasons"]["AMD"],"WIDE_SPREAD")
 def test_unexpected_extra_page(self):
  with self.assertRaises(ValueError):
   audit_pages(["AMD"],[{"quotes":{"AMD":[Q]}},{"quotes":{}}],T)
if __name__=="__main__":unittest.main()
