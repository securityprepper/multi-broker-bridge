import unittest
from datetime import datetime
from v2_rth_small_loss_census_20261110 import analyze


def order(cid, symbol, side, qty, price, clock):
    return dict(client_order_id=cid, symbol=symbol, side=side, status="filled",
                filled_qty=str(qty), filled_avg_price=str(price),
                filled_at="2026-11-10T" + clock + "Z")


def snapshot(orders=None, positions=None):
    return dict(broker_verified=True, recent_orders_complete=True, paper_only=True,
                asof_utc="2026-11-10T18:33:55Z", recent_orders=orders or [],
                positions=positions or [], open_orders_count=0, open_orders=[])


class Tests(unittest.TestCase):
    def test_chicago_rth_and_gross(self):
        s = snapshot([order("MBB-a","AAA","buy",2,100,"15:00:00"),
                      order("MBB-b","AAA","sell",2,99,"15:04:00")])
        r = analyze(s,"2026-11-10")
        self.assertEqual((r["round_trips"],r["gross_realized_usd"]), (1,-2))
        self.assertEqual((r["small_loss_exits"],r["loss_exits_within_6min"]),(1,1))

    def test_prior_session_order_not_included(self):
        s = snapshot([order("MBB-a","AAA","buy",2,100,"12:00:00")])
        self.assertEqual(analyze(s,"2026-11-10")["orders_mbb_rth"],0)

    def test_fifo_mixed_quantities(self):
        s = snapshot([order("MBB-1","AAA","buy",1,100,"15:00:00"),
                      order("MBB-2","AAA","buy",1,105,"15:01:00"),
                      order("MBB-3","AAA","sell",2,106,"15:05:00")])
        self.assertEqual(analyze(s,"2026-11-10")["gross_realized_usd"],7)

    def test_broker_position_match_not_ownership(self):
        s = snapshot([order("MBB-1","AAA","buy",2,100,"15:00:00")],
                     [dict(symbol="AAA",qty="2")])
        r = analyze(s,"2026-11-10")
        self.assertTrue(r["broker_position_quantities_match_mbb_lots"])
        self.assertFalse(r["exclusive_strategy_ownership_proven"])

    def test_oversell_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"unmatched"):
            analyze(snapshot([order("MBB-x","AAA","sell",1,100,"15:00:00")]),"2026-11-10")

    def test_missing_or_unverified(self):
        s = snapshot()
        s["broker_verified"] = False
        with self.assertRaisesRegex(ValueError,"complete"):
            analyze(s,"2026-11-10")

    def test_other_writer_cross_symbol(self):
        s = snapshot([order("MBB-a","AAA","buy",1,100,"15:00:00"),
                      order("FDR-b","AAA","buy",1,100,"15:01:00")],
                     [dict(symbol="AAA",qty="2")])
        self.assertTrue(analyze(s,"2026-11-10")["cross_writer_ambiguity"])

    def test_duplicate_client_id(self):
        s = snapshot([order("MBB-a","AAA","buy",1,100,"15:00:00"),
                      order("MBB-a","AAA","buy",1,100,"15:00:01")])
        with self.assertRaisesRegex(ValueError,"duplicate"):
            analyze(s,"2026-11-10")

    def test_nonzero_open_orders_blocks_audit(self):
        s = snapshot()
        s["open_orders_count"] = 1
        s["open_orders"] = [dict(symbol="AAA")]
        with self.assertRaisesRegex(ValueError,"open broker"):
            analyze(s,"2026-11-10")

    def test_future_fill_is_rejected(self):
        s = snapshot([order("MBB-a","AAA","buy",1,100,"19:00:00")])
        with self.assertRaisesRegex(ValueError,"future"):
            analyze(s,"2026-11-10")

    def test_wrong_local_day_rejected(self):
        with self.assertRaisesRegex(ValueError,"Chicago"):
            analyze(snapshot(),"2026-11-09")


if __name__ == "__main__":
    unittest.main()
