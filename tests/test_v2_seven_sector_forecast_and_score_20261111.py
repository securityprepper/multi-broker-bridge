"""Offline integration tests: sealed forecasts -> distinct future outcomes, no broker calls."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
from research import v2_forward_only_sector_shadow_20261109 as recorder
from research import v2_forward_shadow_score_20261111 as scorer
from research.v2_sector_forecast_policy_20261111 import POLICY_ID,POLICY_SHA256,frozen_forecast

ET=ZoneInfo("America/New_York")
DAY="2026-11-12"
PAST=("2026-11-05","2026-11-06","2026-11-09","2026-11-10","2026-11-11")

def now(hhmm):
    h,m=map(int,hhmm.split(":"))
    return datetime(2026,11,12,h,m,25,tzinfo=ET)
def bar(t, o, c):
    dt=datetime.fromisoformat(DAY+"T"+t+":00").replace(tzinfo=ET).astimezone(timezone.utc)
    return {"t":dt.isoformat(),"o":o,"h":max(o,c),"l":min(o,c),"c":c,"v":100000}
def daily():
    return {s:[{"t":d+"T05:00:00Z","c":100.} for d in PAST] for s in recorder.symbols()}
def market():
    rows=[]
    prices={"09:25":100.0,"09:30":100.2,"09:35":100.3,
            "09:40":100.4,"09:50":100.5,"09:55":100.6,"10:00":100.7,
            "10:30":101.2,"10:40":101.0,"11:00":100.9,"14:35":99.0}
    previous=100.
    for t,c in prices.items():
        rows.append(bar(t,previous,c)); previous=c
    return {s:list(rows) for s in recorder.symbols()}
def fake_fetch(start,frame,cred):
    return daily() if frame=="1Day" else market()

class TestPolicy(unittest.TestCase):
    def setUp(self):
        self.prior=recorder.validate_daily_prior5(daily(),now("09:35"))
        self.bars=recorder.validate_live_bars(market(),now("09:35"))
    def test_all_seven_have_directional_issue(self):
        for slot in recorder.SLOTS:
            t=now(slot)
            history=recorder.validate_live_bars(market(),t)
            res=recorder.asof_signals(t,slot,self.prior,history,issued_at=t)
            self.assertEqual(set(res),set(recorder.SECTORS))
            for sec,row in res.items():
                self.assertEqual(row["shadow_classification"],"UP")
                self.assertEqual(row["peer_confirmed_classification"],"UP")
                self.assertTrue(row["forward_forecast"]["signal_mark"]>0)
                self.assertFalse(row["forward_forecast"]["orders_authorized"])
                self.assertEqual(row["forward_forecast"]["policy_id"],POLICY_ID)
    def test_old_date_not_retroactively_issued(self):
        t=datetime(2026,11,10,9,35,25,tzinfo=ET)
        f=frozen_forecast("energy","XLE",("XOM","CVX"),{},self.prior,t)
        self.assertEqual(f["benchmark_side"],"ABSTAIN")
        self.assertEqual(f["reason"],"ABSTAIN_POLICY_NOT_EFFECTIVE")
    def test_missing_data_explicit_abstain(self):
        t=now("09:35");hist=recorder.validate_live_bars(market(),t)
        hist["SOXX"]={}
        result=recorder.asof_signals(t,"09:35",self.prior,hist,issued_at=t)
        self.assertEqual(result["semiconductors"]["shadow_classification"],"ABSTAIN")
        self.assertEqual(result["semiconductors"]["peer_confirmed_classification"],"ABSTAIN")
        self.assertEqual(result["semiconductors"]["status"],"ABSTAIN_MISSING_ASOF_DATA")
        self.assertIsNone(result["semiconductors"]["forward_forecast"]["signal_mark"])
    def test_tiny_and_mixed_peer_abstention(self):
        t=now("09:35")
        metrics={"XLF":{"from_0930_open_pct":0.01,"observed_price":100.01,"observed_bar_end_ET":t.isoformat()},
                 "JPM":{"from_0930_open_pct":-0.5,"observed_bar_end_ET":t.isoformat()},
                 "BAC":{"from_0930_open_pct":0.5,"observed_bar_end_ET":t.isoformat()}}
        f=frozen_forecast("financials","XLF",("JPM","BAC"),metrics,self.prior,t)
        self.assertEqual(f["benchmark_side"],"ABSTAIN")
        self.assertEqual(f["peer_confirmed_side"],"ABSTAIN")
        metrics["XLF"]["from_0930_open_pct"]=0.55
        f=frozen_forecast("financials","XLF",("JPM","BAC"),metrics,self.prior,t)
        self.assertEqual(f["benchmark_side"],"UP")
        self.assertEqual(f["peer_confirmed_side"],"ABSTAIN")
    def test_incomplete_peer_bar_fails_closed(self):
        t=now("09:35")
        hist=recorder.validate_live_bars(market(),t)
        hist["JPM"]={}
        features=recorder.asof_signals(t,"09:35",self.prior,hist,issued_at=t)
        self.assertEqual(features["financials"]["shadow_classification"],"ABSTAIN")
    def test_forecast_not_affected_by_outcomes(self):
        t=now("09:35")
        prior=self.prior
        first=recorder.asof_signals(t,"09:35",prior,self.bars,issued_at=t)
        future=market()
        for s in future:
            future[s].extend([bar("14:35",100,500),bar("10:30",100,1)])
        later=recorder.validate_live_bars(future,t)
        second=recorder.asof_signals(t,"09:35",prior,later,issued_at=t)
        self.assertEqual(first,second)

class TestScorer(unittest.TestCase):
    def _save_three(self,state):
        for slot in recorder.SLOTS:
            x=recorder.run(now(slot),holiday_check=lambda t:True,fetch=fake_fetch)
            self.assertEqual(x["status"],"RESEARCH_SHADOW_SEALED")
            self.assertEqual(x["benchmark_forecasts_issued"],7)
        self.assertEqual(len(list((state/DAY).glob("*.json"))),3)
    def test_future_scoring_separated_with_exact_84_rows(self):
        with tempfile.TemporaryDirectory() as td,patch.dict("os.environ",{"V2_SHADOW_STATE_ROOT":td}):
            state=Path(td)
            self._save_three(state)
            x=scorer.run(now("14:51"),holiday_check=lambda t:True,fetch=fake_fetch)
            self.assertEqual(x["status"],"RESEARCH_OUTCOMES_SEALED")
            self.assertEqual(x["forecast_rows"],84)
            self.assertEqual(x["orders_submitted"],0)
            saved=json.loads((state/"scores"/DAY/"1340CT.json").read_text())
            self.assertTrue(saved["capture_complete"])
            self.assertEqual(saved["forecast_policy_sha256"],POLICY_SHA256)
            self.assertTrue(saved["signals_and_outcomes_are_separate_immutable_files"])
            rows=saved["scores"]
            r=next(a for a in rows if a["sector"]=="financials" and a["slot_ET"]=="09:35"
                   and a["arm"]=="benchmark_side" and a["horizon"]=="flat")
            self.assertEqual(r["forecast"],"UP")
            self.assertEqual(r["future_mark"],99.)
            self.assertEqual(r["direction"],"MISS")
            original=json.loads((state/DAY/"0935.json").read_text())
            self.assertNotIn("future_mark",str(original))
            y=scorer.run(now("14:52"),holiday_check=lambda t:True,
                         fetch=lambda *a: (_ for _ in ()).throw(AssertionError("scored twice")))
            self.assertEqual(y["status"],"SCORES_ALREADY_SEALED")
    def test_actual_issue_clock_after_data_collection(self):
        with tempfile.TemporaryDirectory() as td,patch.dict("os.environ",{"V2_SHADOW_STATE_ROOT":td}):
            t=now("09:35")
            calls=[]
            def fget(time,frame,cred):
                calls.append(frame)
                return fake_fetch(time,frame,cred)
            def issued():
                self.assertEqual(calls,["1Day","5Min"])
                return t+timedelta(seconds=17)
            x=recorder.run(t,holiday_check=lambda v:True,fetch=fget,issue_clock=issued)
            self.assertEqual(x["status"],"RESEARCH_SHADOW_SEALED")
            doc=json.loads((Path(td)/DAY/"0935.json").read_text())
            self.assertEqual(doc["forecast_actual_issued_at_ET"],(t+timedelta(seconds=17)).isoformat())
            for sector in recorder.SECTORS:
                self.assertEqual(doc["sectors"][sector]["forward_forecast"]["signal_recorded_at_ET"],
                                 (t+timedelta(seconds=17)).isoformat())
    def test_too_late_after_get_never_seals(self):
        with tempfile.TemporaryDirectory() as td,patch.dict("os.environ",{"V2_SHADOW_STATE_ROOT":td}):
            t=now("09:35")
            with self.assertRaises(ValueError):
                recorder.run(t,holiday_check=lambda v:True,fetch=fake_fetch,
                             issue_clock=lambda:t+timedelta(minutes=2))
            self.assertFalse((Path(td)/DAY/"0935.json").exists())
    def test_original_seals_never_backfilled(self):
        with tempfile.TemporaryDirectory() as td,patch.dict("os.environ",{"V2_SHADOW_STATE_ROOT":td}):
            state=Path(td)
            self._save_three(state)
            before={p.name:p.read_bytes() for p in (state/DAY).glob("*.json")}
            scorer.run(now("14:51"),holiday_check=lambda t:True,fetch=fake_fetch)
            after={p.name:p.read_bytes() for p in (state/DAY).glob("*.json")}
            self.assertEqual(before,after)
    def test_score_rejects_old_schema_and_mismatched_hash(self):
        with tempfile.TemporaryDirectory() as td,patch.dict("os.environ",{"V2_SHADOW_STATE_ROOT":td}):
            self._save_three(Path(td))
            p=Path(td)/DAY/"0935.json"
            data=json.loads(p.read_text())
            data["schema_version"]=1
            with self.assertRaises(ValueError):
                scorer.validate_seal(json.dumps(data).encode(),DAY,"09:35")
            data["schema_version"]=2
            data["forecast_policy_sha256"]="invalid"
            with self.assertRaises(ValueError):
                scorer.validate_seal(json.dumps(data).encode(),DAY,"09:35")
    def test_outcomes_before_horizon_never_poll(self):
        with patch.dict("os.environ",{"V2_SHADOW_STATE_ROOT":"/tmp/nonexistent"}):
            x=scorer.run(now("11:00"),holiday_check=lambda t:True,
                         fetch=lambda *a: (_ for _ in ()).throw(AssertionError("fetched early")))
            self.assertEqual(x["status"],"NOT_SCORE_TIME")
    def test_policy_not_effective_nov11_no_score_or_fetch(self):
        t=datetime(2026,11,11,16,15,25,tzinfo=ET)
        x=scorer.run(t,holiday_check=lambda _:True,
                     fetch=lambda *a: (_ for _ in ()).throw(AssertionError("fetched pre-policy")))
        self.assertEqual(x["status"],"POLICY_NOT_YET_EFFECTIVE_NO_SCORE")
        self.assertEqual(x["market_data_requests"],0)
    def test_pause_never_fetches_or_reads_broker(self):
        x=scorer.run(now("14:51"),holiday_check=lambda t:False,
                     fetch=lambda *a: (_ for _ in ()).throw(AssertionError("fetched while paused")))
        self.assertEqual(x["status"],"HOLIDAY_PAUSED_NO_SCORE_OR_POLL")
        self.assertEqual(x["orders_submitted"],0)
    def test_no_prior_issued_forecasts_no_get(self):
        with tempfile.TemporaryDirectory() as td,patch.dict("os.environ",{"V2_SHADOW_STATE_ROOT":td}):
            x=scorer.run(now("14:51"),holiday_check=lambda t:True,
                         fetch=lambda *a: (_ for _ in ()).throw(AssertionError("fetched no forecast")))
            self.assertEqual(x["status"],"NO_NEW_SCHEMA_FORECAST_SEALS")
    def test_tiny_not_credited_as_success(self):
        self.assertEqual(scorer.score_one("UP",100,100.01)["direction"],"TINY_NOT_A_HIT")
        self.assertEqual(scorer.score_one("DOWN",100,99.99)["direction"],"TINY_NOT_A_HIT")
        self.assertEqual(scorer.score_one("UP",100,100)["direction"],"TINY_NOT_A_HIT")
        self.assertEqual(scorer.score_one("DOWN",100,100.5)["direction"],"MISS")
        self.assertEqual(scorer.score_one("UP",100,101)["direction"],"HIT")
        self.assertEqual(scorer.score_one("ABSTAIN",100,110)["direction"],"ABSTAIN")
    def test_missing_outcomes_not_hits(self):
        self.assertEqual(scorer.score_one("DOWN",100,None)["direction"],"MISSING_OUTCOME")
    def test_no_pushover_or_order_interface(self):
        self.assertFalse(hasattr(scorer,"place_order"))
        self.assertFalse(hasattr(scorer,"submit_order"))
        self.assertFalse(hasattr(scorer,"pushover"))
if __name__=="__main__":
    unittest.main()
