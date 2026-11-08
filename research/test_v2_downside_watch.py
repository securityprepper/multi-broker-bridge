import unittest
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from research import v2_downside_watch_only as watch

E=ZoneInfo("America/New_York")

class WatchOnlyTests(unittest.TestCase):
    def test_sunday_closed_and_no_order_api(self):
        day=datetime(2026,11,8,16,0,tzinfo=E)
        self.assertEqual(watch.run(now=day,send=False)["status"],"SESSION_CLOSED")
        self.assertFalse(hasattr(watch,"paper_api"))
        self.assertFalse(hasattr(watch,"submit_order"))

    def test_sunday_boats_targets_monday(self):
        when=datetime(2026,11,8,20,5,tzinfo=E)
        target,feed=watch.session_and_feed(when)
        self.assertEqual(str(target),"2026-11-09")
        self.assertEqual(feed,"boats")

    def test_thursday_evening_friday_and_friday_evening_closed(self):
        t=datetime(2026,11,5,18,0,tzinfo=E)
        self.assertEqual(str(watch.session_and_feed(t)[0]),"2026-11-06")
        self.assertEqual(watch.session_and_feed(datetime(2026,11,6,20,10,tzinfo=E)),(None,None))

    def test_severe_sector_is_not_order_permission(self):
        prices={s:Decimal("100") for s in watch.UNIVERSE}
        past_current={s:(Decimal("99"),Decimal("97")) for s in watch.UNIVERSE}
        result=watch.classify(prices,past_current)
        self.assertTrue(result["sector_severe"])
        self.assertIn("AMD",result["stock_watch"])
        self.assertFalse(result.get("order_permissions",False))

    def test_no_sector_alert_without_soxx(self):
        prices={s:Decimal("100") for s in watch.UNIVERSE}
        ticks={s:(Decimal("99"),Decimal("97")) for s in watch.UNIVERSE if s!="SOXX"}
        self.assertFalse(watch.classify(prices,ticks)["sector_severe"])

    def test_severe_risk_dry_run_does_not_send(self):
        now=datetime(2026,11,9,7,10,tzinfo=E)
        prior={s:Decimal("100") for s in watch.UNIVERSE}
        ticks={s:(Decimal("99"),Decimal("97")) for s in watch.UNIVERSE}
        with patch.object(watch,"market_snapshot",return_value=(prior,ticks,now)),patch.object(watch,"push") as p:
            result=watch.run(now=now,send=False)
            self.assertEqual(result["status"],"SECTOR_SEVERE")
            self.assertFalse(result["order_permissions"])
            p.assert_not_called()

    def test_stock_urgent_after_2point5_percent_and_1percent_15min(self):
        prior={s:Decimal("100") for s in watch.UNIVERSE}
        # 2.6% since regular close, 1.1% over 15 minutes.
        observed={"AMD":(Decimal("98.48"),Decimal("97.40"))}
        risk=watch.classify(prior,observed)
        self.assertIn("AMD",risk["stock_urgent"])
        self.assertFalse(risk["sector_severe"])
        self.assertNotIn("MU",risk["stock_urgent"])

    def test_stock_urgency_requires_both_drop_dimensions(self):
        prior={s:Decimal("100") for s in watch.UNIVERSE}
        observed={"AMD":(Decimal("97.60"),Decimal("97.40")),
                  "MU":(Decimal("99.40"),Decimal("98.50"))}
        risk=watch.classify(prior,observed)
        self.assertEqual(risk["stock_urgent"],[])

    def test_independent_stock_alert_keys_are_not_shared(self):
        import tempfile, pathlib, json
        from unittest.mock import patch
        now=datetime(2026,11,9,7,10,tzinfo=E)
        prior={s:Decimal("100") for s in watch.UNIVERSE}
        observed={"AMD":(Decimal("98.8"),Decimal("97.4")),
                  "MU":(Decimal("98.8"),Decimal("97.4"))}
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            hits=[]
            with patch.object(watch,"market_snapshot",return_value=(prior,observed,now)),patch.object(
                watch,"state_file",return_value=root/"notifications.json"),patch.object(
                watch,"push",side_effect=lambda title,msg:hits.append((title,msg))):
                report=watch.run(now=now,send=True)
                self.assertEqual(report["status"],"STOCK_URGENT")
                self.assertEqual(len(hits),2)
                self.assertTrue(all("V2 TEST" in title for title,msg in hits))
                self.assertTrue(any("AMD" in msg for _,msg in hits))
                self.assertTrue(any("MU" in msg for _,msg in hits))
                watch.run(now=now,send=True)
                self.assertEqual(len(hits),2)
                stored=json.loads((root/"notifications.json").read_text())
                self.assertIn("2026-11-09:stock_urgent:AMD",stored)
                self.assertIn("2026-11-09:stock_urgent:MU",stored)


if __name__=="__main__":
    unittest.main()
