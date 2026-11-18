# November 18, 2026 — Read-only Nov 17 price-followthrough control check

As-of: 2026-11-18T08:28:18.944284+00:00. This is a focused diagnostic of **six** Quality Watch pre-news, 5-minute price-lead observations among ten owner-specified November 17 names, not an independent holdout or a tradable strategy. It is separate from already reported full-universe and 29-name studies.

**Causality:** Selected the first `news_preflight_candidates` recorded in each local, append-only `scans.signal_summary` between 14:30 UTC and 19:15 UTC November 17. The signal-time mark is the **scan's as-of completion** (not an earlier source bar); the reference price is the latest *fully completed* SIP one-minute bar available by that mark. Forward 15-minute, 60-minute, and 13:40 CT returns are subsequent SIP minute closes and are ***price-only proxies***, not receiving-broker executable bid/ask, fills, or after-fee returns. All six research leads had `news_clearance=NOT_YET_CHECKED` and `order_permission=false`. No fresh NEWS_CLEAR_ASOF or actual broker entry was verified. A stock could appear after some of its move already occurred; selection was explicitly targeted and prone to survivorship bias.

The six lead observations were **2/6 up after 15 minutes, 2/6 up after 60 minutes, 2/6 up by 13:40 CT**. Four of the ten examined names (CHRW, FIX, ILMN, ROK) had no matching preflight lead in the selected entry window and remain **nontriggers**, not hypothetical winning trades. Their absence cannot be labeled a data outage without independent coverage evidence. The result is not a new forward profitable edge. Existing strict order/news/holiday gates and no-trade decisions remain unchanged.

| Symbol | First knowable UTC | 15m close % | 60m close % | 13:40 CT close % |
|---|---|---:|---:|---:|
| CRM | 2026-11-17T15:08:57.215418+00:00 | -0.744 | -1.884 | -1.637 |
| GEV | 2026-11-17T14:31:57.215533+00:00 | 0.237 | -2.524 | -2.124 |
| NKE | 2026-11-17T14:36:57.206139+00:00 | -2.359 | -3.656 | -10.017 |
| NOC | 2026-11-17T14:56:57.203241+00:00 | -0.233 | 0.700 | 0.254 |
| PWR | 2026-11-17T14:38:57.196830+00:00 | -0.297 | -1.643 | -1.095 |
| SYK | 2026-11-17T14:44:57.222514+00:00 | 1.392 | 2.397 | 1.670 |

**Next validation** (research only): disjoint sessions and matched negative controls; compare original quote bid/ask at first knowable signal, full spread, fees, stop-first same-bar ties and actual eligible source clearance, excluding failed/unknown permissions. Require 20–30 distinct untouched sessions; do not use this selected date to tune rules. No PAPER/LIVE orders or active source/timer modifications were made.

Raw JSON from the exact run is below for deterministic review.

```json
{
  "asof_utc": "2026-11-18T08:28:18.944284+00:00",
  "experiment": "price_only_proxy_nontrade",
  "data": {
    "CHRW": {
      "status": "NO_EARLY_PRE_FLIGHT_LEAD"
    },
    "CRM": {
      "status": "PRICE_PROXY_ONLY_NO_BID_ASK",
      "source": {
        "signal_knowable_at_utc": "2026-11-17T15:08:57.215418+00:00",
        "observed_bar_at_utc": "2026-11-17T15:07:00+00:00",
        "stock_p5_pre_signal": 0.308,
        "relative_p5_pre_signal": 0.406,
        "reason": "COMPANY_5M_OUTPERFORMS_ETF",
        "news_clearance": "NOT_YET_CHECKED",
        "order_permission": false
      },
      "mark_close": 200.385,
      "mark_bar_available_utc": "2026-11-17T15:08:00+00:00",
      "signal_time_utc": "2026-11-17T15:08:57.215418+00:00",
      "15m": {
        "close": 198.895,
        "change_pct": -0.7436,
        "available_at": "2026-11-17T15:24:00+00:00"
      },
      "60m": {
        "close": 196.61,
        "change_pct": -1.8839,
        "available_at": "2026-11-17T16:09:00+00:00"
      },
      "1340_CT": {
        "close": 197.105,
        "change_pct": -1.6368
      }
    },
    "FIX": {
      "status": "NO_EARLY_PRE_FLIGHT_LEAD"
    },
    "GEV": {
      "status": "PRICE_PROXY_ONLY_NO_BID_ASK",
      "source": {
        "signal_knowable_at_utc": "2026-11-17T14:31:57.215533+00:00",
        "observed_bar_at_utc": "2026-11-17T14:30:00+00:00",
        "stock_p5_pre_signal": 0.859,
        "relative_p5_pre_signal": null,
        "reason": "COMPANY_5M_RISING_ETF_PRICE_UNAVAILABLE",
        "news_clearance": "NOT_YET_CHECKED",
        "order_permission": false
      },
      "mark_close": 781.66,
      "mark_bar_available_utc": "2026-11-17T14:31:00+00:00",
      "signal_time_utc": "2026-11-17T14:31:57.215533+00:00",
      "15m": {
        "close": 783.5145,
        "change_pct": 0.2373,
        "available_at": "2026-11-17T14:47:00+00:00"
      },
      "60m": {
        "close": 761.93,
        "change_pct": -2.5241,
        "available_at": "2026-11-17T15:32:00+00:00"
      },
      "1340_CT": {
        "close": 765.06,
        "change_pct": -2.1237
      }
    },
    "ILMN": {
      "status": "NO_EARLY_PRE_FLIGHT_LEAD"
    },
    "NKE": {
      "status": "PRICE_PROXY_ONLY_NO_BID_ASK",
      "source": {
        "signal_knowable_at_utc": "2026-11-17T14:36:57.206139+00:00",
        "observed_bar_at_utc": "2026-11-17T14:35:00+00:00",
        "stock_p5_pre_signal": 0.973,
        "relative_p5_pre_signal": 0.667,
        "reason": "COMPANY_5M_OUTPERFORMS_ETF",
        "news_clearance": "NOT_YET_CHECKED",
        "order_permission": false
      },
      "mark_close": 40.48,
      "mark_bar_available_utc": "2026-11-17T14:36:00+00:00",
      "signal_time_utc": "2026-11-17T14:36:57.206139+00:00",
      "15m": {
        "close": 39.525,
        "change_pct": -2.3592,
        "available_at": "2026-11-17T14:52:00+00:00"
      },
      "60m": {
        "close": 39,
        "change_pct": -3.6561,
        "available_at": "2026-11-17T15:37:00+00:00"
      },
      "1340_CT": {
        "close": 36.425,
        "change_pct": -10.0173
      }
    },
    "NOC": {
      "status": "PRICE_PROXY_ONLY_NO_BID_ASK",
      "source": {
        "signal_knowable_at_utc": "2026-11-17T14:56:57.203241+00:00",
        "observed_bar_at_utc": "2026-11-17T14:55:00+00:00",
        "stock_p5_pre_signal": 0.332,
        "relative_p5_pre_signal": 0.368,
        "reason": "COMPANY_5M_OUTPERFORMS_ETF",
        "news_clearance": "NOT_YET_CHECKED",
        "order_permission": false
      },
      "mark_close": 550.25,
      "mark_bar_available_utc": "2026-11-17T14:56:00+00:00",
      "signal_time_utc": "2026-11-17T14:56:57.203241+00:00",
      "15m": {
        "close": 548.97,
        "change_pct": -0.2326,
        "available_at": "2026-11-17T15:12:00+00:00"
      },
      "60m": {
        "close": 554.1,
        "change_pct": 0.6997,
        "available_at": "2026-11-17T15:57:00+00:00"
      },
      "1340_CT": {
        "close": 551.645,
        "change_pct": 0.2535
      }
    },
    "PWR": {
      "status": "PRICE_PROXY_ONLY_NO_BID_ASK",
      "source": {
        "signal_knowable_at_utc": "2026-11-17T14:38:57.196830+00:00",
        "observed_bar_at_utc": "2026-11-17T14:37:00+00:00",
        "stock_p5_pre_signal": 0.342,
        "relative_p5_pre_signal": 0.218,
        "reason": "COMPANY_5M_OUTPERFORMS_ETF",
        "news_clearance": "NOT_YET_CHECKED",
        "order_permission": false
      },
      "mark_close": 597.3075,
      "mark_bar_available_utc": "2026-11-17T14:38:00+00:00",
      "signal_time_utc": "2026-11-17T14:38:57.196830+00:00",
      "15m": {
        "close": 595.535,
        "change_pct": -0.2967,
        "available_at": "2026-11-17T14:54:00+00:00"
      },
      "60m": {
        "close": 587.495,
        "change_pct": -1.6428,
        "available_at": "2026-11-17T15:39:00+00:00"
      },
      "1340_CT": {
        "close": 590.77,
        "change_pct": -1.0945
      }
    },
    "ROK": {
      "status": "NO_EARLY_PRE_FLIGHT_LEAD"
    },
    "SYK": {
      "status": "PRICE_PROXY_ONLY_NO_BID_ASK",
      "source": {
        "signal_knowable_at_utc": "2026-11-17T14:44:57.222514+00:00",
        "observed_bar_at_utc": "2026-11-17T14:43:00+00:00",
        "stock_p5_pre_signal": 0.184,
        "relative_p5_pre_signal": 0.34,
        "reason": "COMPANY_5M_OUTPERFORMS_ETF",
        "news_clearance": "NOT_YET_CHECKED",
        "order_permission": false
      },
      "mark_close": 310.25,
      "mark_bar_available_utc": "2026-11-17T14:44:00+00:00",
      "signal_time_utc": "2026-11-17T14:44:57.222514+00:00",
      "15m": {
        "close": 314.57,
        "change_pct": 1.3924,
        "available_at": "2026-11-17T15:00:00+00:00"
      },
      "60m": {
        "close": 317.6868,
        "change_pct": 2.397,
        "available_at": "2026-11-17T15:45:00+00:00"
      },
      "1340_CT": {
        "close": 315.43,
        "change_pct": 1.6696
      }
    }
  }
}
```
