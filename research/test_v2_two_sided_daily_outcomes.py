"""No-lookahead and overlapped-threshold tests for daily outcomes."""
import unittest
from datetime import date,datetime,time,timedelta
from research.v2_stock_risk_dayphase import ET,T5
from research.v2_two_sided_daily_outcomes import (
  signal,first_observable,score_profit,subset_metrics
)


class TwoSidedDailyTests(unittest.TestCase):
    def test_negative_overlap(self):
        self.assertTrue(signal("down",100,98.5,97.5,.025,.01))
        self.assertFalse(signal("down",100,98.5,97.6,.025,.01))
        self.assertFalse(signal("down",100,99,97.6,.025,.02))

    def test_positive_overlap(self):
        self.assertTrue(signal("up",100,101.5,102.55,.025,.01))
        self.assertFalse(signal("up",100,101.5,102.45,.025,.01))

    def test_earliest_observable_bar_close(self):
        target=date(2026,3,9)
        prev=date(2026,3,6)
        t=lambda m:datetime.combine(target,time(9,m),ET)
        bars={t(30):[99,100,98,99,1000],t(35):[99,99,98,98.9,1000],
              t(40):[99,101,98.5,99,1000],t(45):[99.2,102.6,99,102.6,1000],
              t(50):[102.7,103,102.3,102.8,1000]}
        msg=first_observable(bars,target,prev,100,'up',.025,.01,{'rth_open_hour'})
        self.assertEqual(msg['asof'],t(50).isoformat())
        self.assertEqual(msg['next_open'],102.7)
        self.assertIsNone(first_observable({k:v for k,v in bars.items() if k<t(45)},
                           target,prev,100,'up',.025,.01,{'rth_open_hour'}))
        self.assertIsNone(first_observable(bars,target,prev,100,'up',.025,.01,{'premarket'}))

    def test_slippage_reduces_gain(self):
        self.assertLess(score_profit(100,104),4.0)
        self.assertGreater(score_profit(100,104),3.6)
        self.assertIsNone(score_profit(None,104))

    def test_labels_are_scored_not_input(self):
        a=dict(major_up=True,major_down=False,up_25_10=dict(
            drawdown_pct=2.6,pnl_to14_pct=-1.0))
        b=dict(major_up=False,major_down=True,up_25_10=dict(
            drawdown_pct=2.6,pnl_to14_pct=0.4))
        x=subset_metrics([a,b],'up_25_10','up')
        self.assertEqual((x['hits'],x['false_alarms'],x['favorable_proxy_outcomes']), (1,1,1))


if __name__=="__main__":
    unittest.main()
