import json
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
from research.v2_news_watch_readonly import ingest,run

T=datetime(2026,11,11,7,0,tzinfo=timezone.utc)
def article(id):
 return {"id":id,"created_at":(T-timedelta(seconds=20)).isoformat(),
         "headline":"Company says will report earnings","symbols":["AMD"],"source":"test"}
class FirstSeenTests(unittest.TestCase):
 def test_poll_receipt_after_fetch(self):
  with tempfile.TemporaryDirectory() as tmp:
   state=Path(tmp)/"state.json"
   with patch.dict("os.environ",{"V2_NEWS_WATCH_STATE":str(state),"CREDENTIALS_DIRECTORY":tmp}):
    x=run(now=T,news_fetcher=lambda *_:[article("x")],holiday_checker=lambda *_:True)
   data=json.loads(state.read_text())
   self.assertEqual(x["new_articles"],1)
   self.assertEqual(data["poll_started_at_utc"],T.isoformat())
   received=datetime.fromisoformat(data["poll_completed_at_utc"])
   self.assertGreater(received,T)
   self.assertEqual(data["recent"][0]["observed_at_utc"],received.isoformat())
   self.assertFalse(data["historical_first_seen_backfill_permitted"])
 def test_dedup_stable_across_identical_fetches(self):
  state,added=ingest([article("a"),article("b")],T,{})
  state2,added2=ingest([article("a"),article("b")],T+timedelta(seconds=10),state)
  self.assertEqual(len(added2),0)
  self.assertEqual(state2["seen"],["a","b"])
 def test_dedup_replay_4000_stable(self):
  before={"seen":[str(n) for n in range(3999)],"recent":[]}
  state,added=ingest([article("3999"),article("4000")],T,before)
  self.assertEqual(state["seen"][0],"1")
  self.assertEqual(state["seen"][-1],"4000")
  self.assertEqual(len(state["seen"]),4000)
 def test_missing_old_article_reappears_only_after_eviction(self):
  prior={"seen":[str(n) for n in range(4000)],"recent":[]}
  state,added=ingest([article("3999"),article("4000")],T,prior)
  self.assertEqual(len(added),1)
  self.assertEqual(state["seen"][0],"1")
 def test_invalid_holiday_does_not_fetch(self):
  with patch("research.v2_news_watch_readonly.get_news",side_effect=AssertionError("called")):
   self.assertEqual(run(now=T,news_fetcher=lambda *_:self.fail("fetch"),
    holiday_checker=lambda *_:False)["market_data_requests"],0)
if __name__=="__main__":unittest.main()
