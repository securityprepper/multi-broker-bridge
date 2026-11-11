# V2 research — MBB latest-quote fixed-scan-clock rejection (2026-11-10 CT)

## New concrete source defect
Active V1 `multi_broker_bridge/auto_paper.py` captures `now=datetime.now(timezone.utc)` at the START of every once-per-minute run. Inside `run(now)`, the code retrieves PAPER account, positions, working orders, local state, 47 minutes of one-minute SIP/BOATS bars across its configured symbol batches, and FINALLY `/v2/stocks/quotes/latest`. The most recently received quote is then compared to the **old scan-start** `now` using `0 <= now-quote_time <= 100 seconds`.

A liquid stock may have an exchange quote time later than scan start but earlier than quote HTTP receipt. The existing check incorrectly calls it a future quote and drops it, reporting the broad `NO_FRESH_BID_ASK` reason. At 08:46:40 CT on Nov 10 the MBB systemd scan began; its journal result was emitted 08:46:46 and rejected all 13 semiconductor BUY_WATCH symbols for that reason. Independently obtained historical SIP AMD/AMAT quotes were 0.22s/0.13s old at 08:46:46 (0.052%/0.236% spreads), meaning both timestamps were ~5.8s AFTER the executor's START. **This strongly supports a real scan-clock mismatch but cannot prove exactly which raw quotes the original `quotes/latest` response contained.**

## Minimal isolated V2 source fix — no V1 release
Research branch `research/rebound-v2-conditional-exits` now modifies ONLY the equivalent isolated `multi_broker_bridge/auto_paper.py` quote validation:
```python
quoted = _fetch_json(DATA_HOST + "/v2/stocks/quotes/latest?" + qparams, headers=headers)
quote_received_at = datetime.now(timezone.utc)
# ...
if quote_time.tzinfo is None or not timedelta(0) <= quote_received_at-quote_time <= MAX_QUOTE_AGE:
    continue
```
This uses a separately observed post-GET receipt clock for quote age, but keeps `MAX_QUOTE_AGE=100 seconds`, `MAX_SPREAD=1%`, positive prices, uncrossed bid/ask, genuine-future rejection, duplicate and account/holiday gates, 13:15 CT entry cutoff, 13:40 flat, and PAPER/LIVE isolation unchanged. Original completed-bar point-in-time rules continue referencing scan start, NOT the newly fetched quote receipt.

### Verification
- Mocked genuine `fetch_bars_and_quotes` with no network and delayed latest quote: V2 **accepts** a quote received after scan start; correctly rejects truly future quote relative to its receipt clock, >100-sec stale quotes, crossed, zero bids and >1% spreads.
- Ten independent quote timestamp/reason tests and seven direct patched-fetcher tests: **17/17 pass** on authorized www3 isolated clone; plus existing `tests.test_auto_paper` **7/7 pass**. No real orders/Alpaca POST.
- Previous GET-only historical two-minute replay reached Alpaca's 10,000 historical trade/quote page limit; its initial AMD/AMAT-only response has continuation token. Eleven other missing symbols are **not proven absent**. Separate seven tests already cover pagination integrity.
- The Nov 10 journal 00:00–13:16 CT contains 946 SCAN_COMPLETE records, 80 with BUY_WATCH: 456 repeated quote-related skips and 108 reentry skips. No attempt to call them distinct missed fills or to estimate avoidable P&L.

## Independent scan-duration correlation — additional read-only journal proof
Parsed UTC journal metadata from `journalctl --output=json`, pairing scan START events with SCAN_COMPLETE results from 2026-11-10 00:00–13:16 Chicago. Across 946 scans, 80 had at least one BUY_WATCH. Of these, **72 had one or more NO_FRESH_BID_ASK symbol skips** (median scan duration 5.96s; 54/72 lasted at least 5 seconds), while **8 had BUY_WATCH but no quote skips** (median 3.02s; 0/8 lasted at least 5 seconds). The 08:46 scan lasted 6.21s and had 13 quote skips. This strong association fits the frozen scan-start clock defect; it does NOT prove causation or recover original per-symbol latest responses. It also does not prove any absent PAPER fill would have been profitable.

## Still unresolved
1. Exact 456-skip breakdown requires independently timestamped ORIGINAL or new prospective `/quotes/latest` raw-response and receipt-time evidence. The historic live response was not retained. An independent GET-only research observer or explicit minimal V1 diagnostic logging is needed; **do not claim precise historical allocation**.
2. The fix is on V2 research branch only. The dirty active V1 checkout /opt/securityprepper/multi-broker-bridge and enabled systemd PAPER timer were **not altered**. A separate owner-authorized PAPER security rollout with receipt-time observability, valid PAPER broker status, broker position/order dedup, and full-day exit protections is needed before installing this V2 change in V1.
3. No strategy P&L profitability is implied by making quotes available; BUY_WATCH still needs independent expected-after-cost edge, adequate risk, prior-position and cross-strategy safety. Do not loosen quote validity or submit orders merely to boost fill rate.
4. The separate Trading Opportunities recommendation-to-Alpaca PAPER bridge is not commissioned; restricted database identities, cross-executor locking, and protective-fill/flatten certification remain outstanding.

**Safety conclusion:** Fix the timestamp comparison in a separately reviewed PAPER-only release, not by relaxing the quote age/spread limits. Continue genuinely new catalyst research rather than repeating previously losing sector-only variants.
