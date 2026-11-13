"""Broker-free tests for MBB receiving-account PAPER news and five-minute gate."""
import os
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from multi_broker_bridge.paper_buy_safety import (
    PaperBuyBlocked,recent_five_minute_direction,require_mbb_buy_preflight,
    trusted_news_clearance
)
from multi_broker_bridge.trend import Bar

NOW=datetime(2026,11,13,15,30,40,tzinfo=timezone.utc)
SYM="AMD"
def make_bars(closes=(100,100.1,100.2,100.3,100.4,100.5),end=NOW):
    old=end.replace(second=0,microsecond=0)-timedelta(minutes=6)
    out=[]
    for i,c in enumerate(closes):
        c=Decimal(str(c))
        out.append(Bar(SYM,old+timedelta(minutes=i),c,c,c))
    return out

class FiveMinDirectionTest(unittest.TestCase):
    def expect_block(self,reason,rows=None,bid="100.50",ask="100.51",now=NOW):
        with self.assertRaises(PaperBuyBlocked) as cm:
            recent_five_minute_direction(SYM,rows if rows is not None else make_bars(),now,Decimal(bid),Decimal(ask))
        self.assertEqual(cm.exception.reason,reason)
    def test_uptrend_uses_existing_completed_bars_no_wait(self):
        v=recent_five_minute_direction(SYM,make_bars(),NOW,Decimal("100.50"),Decimal("100.51"))
        self.assertEqual(v["status"],"PRICE_5M_RISING_ASOF")
        self.assertEqual(v["five_minute_change_pct"],"0.5000")
    def test_five_minute_falling_veto(self):
        self.expect_block("PRICE_5M_DECLINING_AVOID",make_bars((100,99.9,99.8,99.7,99.6,99.5)),bid="99.49",ask="99.51")
    def test_initial_rebound_then_now_dropping_veto(self):
        self.expect_block("PRICE_5M_LAST_COMPLETED_BAR_FALLING",make_bars((100,100.2,100.5,100.7,100.8,100.6)),bid="100.60",ask="100.62")
    def test_flat_watch(self):
        self.expect_block("PRICE_5M_FLAT_WATCH_ONLY",make_bars((100,100,100,100,100,100)),bid="100",ask="100.01")
    def test_spread_and_falling_bid(self):
        self.expect_block("PRICE_5M_DECLINING_AVOID",make_bars(),bid="99.99",ask="100.51")
    def test_quote_crossed(self):
        self.expect_block("PRICE_5M_BID_ASK_CROSSED",make_bars(),bid="101",ask="100")
    def test_gapped_price_data_no_fabrication(self):
        bars=make_bars()
        bars.pop(2)
        self.expect_block("PRICE_5M_INSUFFICIENT_COMPLETED_BARS",bars)
    def test_six_bars_not_consecutive(self):
        bars=make_bars()
        bars[1]=Bar(SYM,bars[1].timestamp-timedelta(seconds=20),bars[1].high,bars[1].low,bars[1].close)
        self.expect_block("PRICE_5M_GAPPED_BARS",bars)
    def test_stale_old_5m_data_rejected(self):
        self.expect_block("PRICE_5M_STALE_COMPLETED_BAR",make_bars(end=NOW-timedelta(minutes=5)))
    def test_unfinished_last_bar_rejected(self):
        self.expect_block("PRICE_5M_INCOMPLETE_BAR",make_bars(end=NOW+timedelta(minutes=1)))
    def test_wrong_symbol_rejected(self):
        bars=make_bars()
        b=bars[-1]
        bars[-1]=Bar("MU",b.timestamp,b.high,b.low,b.close)
        self.expect_block("PRICE_5M_WRONG_OR_UNDATED_BAR",bars)
    def test_missing_quote_decimal_not_accepted(self):
        with self.assertRaises(PaperBuyBlocked):
            recent_five_minute_direction(SYM,make_bars(),NOW,Decimal("NaN"),Decimal("100.6"))
    def test_mock_clear_still_requires_price(self):
        def ok(symbol,now):return {"status":"NEWS_CLEAR_ASOF","evidence_sha256":"a"*64}
        result=require_mbb_buy_preflight(SYM,make_bars(),NOW,Decimal("100.5"),Decimal("100.6"),news_check=ok)
        self.assertEqual(result["status"],"PAPER_BUY_PREFLIGHT_PASS")
        with self.assertRaises(PaperBuyBlocked):
            require_mbb_buy_preflight(SYM,make_bars((100,99,98,97,96,95)),NOW,Decimal("95"),Decimal("95.1"),news_check=ok)
    def test_unknown_news_fails_even_when_price_up(self):
        def none(symbol,now):return {"status":"NEWS_UNKNOWN"}
        with self.assertRaises(PaperBuyBlocked) as cm:
            require_mbb_buy_preflight(SYM,make_bars(),NOW,Decimal("100.5"),Decimal("100.6"),news_check=none)
        self.assertEqual(cm.exception.reason,"NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE")
    def test_no_root_attestation_files_blocks_paper_buy(self):
        with self.assertRaises(PaperBuyBlocked) as cm:
            trusted_news_clearance("ZZZNOFILE",NOW)
        self.assertTrue(cm.exception.reason.startswith("NEWS_"))
    def test_no_live_or_broker_methods_in_reducer(self):
        src=Path(__file__).resolve().parents[1].joinpath("multi_broker_bridge/paper_buy_safety.py").read_text()
        for forbidden in ("paper_api(", "urlopen(", "requests.post(", "IBKR", "Robinhood", "broker_api(", "LIVE_ORDER"):
            self.assertNotIn(forbidden,src)

if __name__=="__main__":unittest.main()
