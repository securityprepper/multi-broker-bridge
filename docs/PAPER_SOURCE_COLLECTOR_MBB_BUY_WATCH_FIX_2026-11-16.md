# PAPER-only MBB BUY_WATCH news-source collector fix — 2026-11-16

Owner approved the correction in this chat by requesting “Fix it.” This is an isolated collector-only deployment; it is **not an order-release authorization**. The prior research finding in RESEARCH_2026-11-16_MBB_BUY_WATCH_CLEARANCE_SELECTION_MISMATCH.md remains an accurate historical record of the previously uncommissioned state.

## Installed on www3.securityprepper.com

- Source file: `/opt/securityprepper/recommendation-paper-bridge/recommendation_paper_bridge/news_source_collector.py`
- Original SHA-256: `6e76c4249853343b4ca421703e4aa948103268d57f7a56117a0d740febec4dd4`
- Installed SHA-256: `f8ffca4413e10809e7d1ad62c025261d31823f9b9fd201d634323359e0731d51`
- Persistent rollback copy: `/var/lib/securityprepper-news-source-collector/pre_mbb_candidate_backup_20261116.py`
- Persistent unit tests: `/opt/securityprepper/recommendation-paper-bridge/tests/test_news_source_mbb_watch_20261116.py`
- Research branch at review time: `c099e276ff26c33ca967342e04795254bfbe3dee`; local divergent research worktree and dirty MBB production checkout were NOT modified.

## Behavior

The GET-only source collector reads the timestamped latest completed `SCAN_COMPLETE` from `trading-sector-paper-executor.service` through a fixed `journalctl` command (no shell), ignoring events older than 90s or from the future. It validates `buy_watch_symbols` list shape (up to 500 input rows), ticker syntax, pre-existing approved issuer RSS membership, deduplicates, and prioritizes MBB-approved demand before Quality Watch and the original six-symbol baseline; total selection cap remains 32. On journal error or malformed data, it retains Quality Watch and the baseline. A signal is only a reason to screen: it NEVER supplies `NEWS_CLEAR_ASOF` and bypasses no adverse-news, SEC/CIK, receipt, publisher or broker safeguards.

## Verification

- 13 targeted selection tests passed, including stale/future/latest, malformed, denied symbols, dedup, fallback, bounded read, runner timeout/error, no broker transport.
- 10 historical collector evidence tests passed with two prior test stubs adjusted solely for the existing `issuer_name` keyword.
- Installed production module re-imported and 13 persisted selection tests passed.
- Natural scheduled run at 2026-11-16 10:07:15 America/Chicago completed with unit `Result=success`, six source bundles, `broker_orders=0`, `clearance_published_by_collector=false`. Downstream clearance publisher 10:07:45 returned `Result=success`.
- MBB's latest completed real scan at the acceptance timestamp contained no qualifying issuer-feed watch; positive watch selection verified in unit/replay tests, **not yet observed in a live nonempty MBB watch cycle**.
- No change to active V1 PAPER/LIVE executor, order permissions, protective orders, session timers, holiday publisher or source clear eligibility conditions.

## Exact deployed code delta

```diff
--- a/recommendation_paper_bridge/news_source_collector.py
+++ b/recommendation_paper_bridge/news_source_collector.py
@@ -11,7 +11,7 @@
 A dynamic candidate shortlist never substitutes for original source evidence.
 """
 from __future__ import annotations
-import argparse,datetime as dt,email.utils,hashlib,json,os,re,sqlite3,stat,tempfile,gzip
+import argparse,datetime as dt,email.utils,hashlib,json,os,re,sqlite3,stat,tempfile,gzip,subprocess
 from pathlib import Path
 from urllib.parse import urlencode,urlparse
 from urllib.request import Request,build_opener,HTTPRedirectHandler
@@ -400,6 +400,54 @@
 # blanket scan should bypass contemporaneous issuer/feed verification.
 MAX_SYMBOLS_PER_CYCLE=32
 BASELINE_SYMBOLS=("FTV","AMD","INTC","NVDA","MRVL","FROG")
+MBB_SCAN_SERVICE="trading-sector-paper-executor.service"
+MBB_SCAN_MAX_AGE=dt.timedelta(seconds=90)
+MBB_SYMBOL=re.compile(r"[A-Z][A-Z0-9.]{0,11}")
+
+def recent_mbb_buy_watch(*,now,runner=subprocess.run):
+    """Untrusted demand hints from latest completed, timestamped MBB PAPER scan.
+
+    No broker access, no clearance assertion. Never use stale/future/unbounded
+    journal records. If journal access or schema fails, safely use old shortlist.
+    """
+    if not isinstance(now,dt.datetime) or now.tzinfo is None:
+        return []
+    now=now.astimezone(dt.timezone.utc)
+    command=["/usr/bin/journalctl","--quiet","--no-pager","-o","json",
+             "-u",MBB_SCAN_SERVICE,
+             "--since",(now-MBB_SCAN_MAX_AGE).isoformat(),
+             "--until",now.isoformat(),"-n","256"]
+    try:
+        proc=runner(command,capture_output=True,text=True,timeout=3)
+    except (OSError,subprocess.SubprocessError):
+        return []
+    if (proc.returncode!=0 or not isinstance(proc.stdout,str)
+        or len(proc.stdout)>2_000_000):
+        return []
+    latest=None
+    watch=None
+    for line in proc.stdout.splitlines():
+        if len(line)>200_000:continue
+        try:
+            record=json.loads(line)
+            timestamp=dt.datetime.fromtimestamp(
+                int(record["__REALTIME_TIMESTAMP"])/1_000_000,dt.timezone.utc)
+            message=json.loads(record["MESSAGE"])
+        except (KeyError,ValueError,TypeError,OverflowError,UnicodeError):
+            continue
+        age=now-timestamp
+        if not(dt.timedelta(0)<=age<=MBB_SCAN_MAX_AGE):continue
+        if not isinstance(message,dict) or message.get("status")!="SCAN_COMPLETE":
+            continue
+        if latest is None or timestamp>latest:
+            latest=timestamp
+            watch=message.get("buy_watch_symbols")
+    if not isinstance(watch,list) or len(watch)>500:
+        return []
+    # Only independently approved issuer feeds. A WATCH is never a clearance.
+    return list(dict.fromkeys(symbol for symbol in watch
+        if isinstance(symbol,str) and MBB_SYMBOL.fullmatch(symbol)
+        and symbol in ISSUER_RSS))[:MAX_SYMBOLS_PER_CYCLE]
 
 def candidates(db=SQLITE,*,now=None):
     """Prioritize *current* qualified source candidates, not static six.
@@ -425,9 +473,10 @@
                         result.append(symbol)
     except (OSError,ValueError,TypeError,sqlite3.Error,KeyError):
         pass
-    # Preserve all baseline coverage after prioritized current names. Never
-    # allow an unsupported symbol, duplicate or unbounded universe scan.
-    return list(dict.fromkeys(result+list(BASELINE_SYMBOLS)))[:MAX_SYMBOLS_PER_CYCLE]
+    # Most recent verified-timestamp MBB PAPER demand takes priority; Quality
+    # Watch and the original six-symbol baseline remain intact as fallbacks.
+    mbb=recent_mbb_buy_watch(now=now)
+    return list(dict.fromkeys(mbb+result+list(BASELINE_SYMBOLS)))[:MAX_SYMBOLS_PER_CYCLE]
 
 def run(now=None,clock=lambda:dt.datetime.now(dt.timezone.utc),source=OUTPUT,status=STATUS,
     holiday=HOLIDAY_GATE,ciks=CIK_MAP,chosen=None):
```

Rollback if necessary: after validating an unpaused fresh holiday gate and ensuring the collector service is not in the middle of an execution, atomically restore the saved rollback copy to the same source file with original root owner and 0644 permissions; do not change service units, timers, or any active broker executor.


## Prospective live candidate-selection acceptance (read-only, Nov 16 10:39 CT)

The independently sampled journal interval from 10:07–10:39 America/Chicago (after collector deployment) contained **38** completed MBB executor scan events and **32** successful JSON collector events. Four MBB scan events contained one or more issuer-feed-approved BUY_WATCH symbols, totaling **13 approved-watch appearances** (repeat symbols across scans are NOT distinct securities/trades). In collector cycles completed within 90 seconds after those scans, **13/13 watch appearances were selected**; **zero missing** in this bounded sample. The test matched service journal publication timestamps and explicitly checked the actual collector `selected_symbols`, not only the new selection code. This closes the previously unobserved live nonempty-watch acceptance condition for this sampled period, but is **not** proof that all eligible companies produce complete valid original news evidence, publisher `NEWS_CLEAR_ASOF`, broker qualification, fills or positive P/L. Research collected no broker data or order permissions from this sample; historical 1/6 miss replay remains a distinct, earlier period.

Independent broker GET-only history read during the same research window returned 277 unique FILL activities since Nov 9, with **0** new activities on/after Nov 13 00:00 UTC for the one credential-scoped PAPER account; other accounts remain UNKNOWN. No new after-fee trading edge. Neither collector nor broker execution settings changed during this verification.
