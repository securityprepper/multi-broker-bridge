# V2 prospective-only sector shadow recorder — installed Nov 9 2026

**Status:** Isolated READ-ONLY host service and timer installed and ENABLED on authorized www3; NO broker access, NO orders, NO alerts, NO changes to enabled V1 PAPER/LIVE monitors, stop protection or orders. This is independent from V1 execution and existing notification systems.

## Why
Previous 52-week data were used in repeated exploratory policy selection. The chronologically later periods are NOT genuinely blind to human-led research. To determine whether any early bearish/bullish sector setup really predicts subsequent movement we need an immutable **first-observed timestamp and signal** saved *before* the future 60-minute or 13:40 Chicago outcome is available. It must not be backfilled or relabeled.

## Installed systemd

- `securityprepper-v2-forward-shadow.timer` enabled/active, `OnCalendar` Monday–Friday **09:35:25, 09:45:25 and 10:05:25 America/New_York**. Verified by `systemd-analyze calendar`: next prospective cycle Tuesday Nov10 2026 08:35:25, 08:45:25 and 09:05:25 **Chicago** (if trusted holiday gate stays unpaused).
- Unit `securityprepper-v2-forward-shadow.service`, owned code `/opt/securityprepper/v2-forward-shadow/research/v2_forward_only_sector_shadow_20261109.py`, runs `alpacafeed:sectorread` only with DATA-only Alpaca credentials provided by systemd `LoadCredential`. No broker/order credentials, POSTs, notifications or Pushover.
- GET-only Alpaca SIP 5-minute bars for **23 sector ETFs and peers** (SOXX/AMD/MU/NVDA; GDX/NEM/AEM/KGC; XLE/XOM/CVX; XLF/JPM/BAC; XLI/CAT/GE; XLV/UNH/LLY; IGV/MSFT/CRM), plus five preceding COMPLETED daily bar dates for each symbol. Reject missing/duplicated/conflicting daily history; reject unfinished / future bar candles.
- When signal period begins, save once exclusively to `/var/lib/securityprepper-v2-forward-shadow/observations/YYYY-MM-DD/HHMM.json` (see caveat below). **The actual installed path is `/var/lib/securityprepper-v2-forward-shadow/YYYY-MM-DD/HHMM.json`**, with directory mode 0700 / JSON mode 0600, no prior record overwrite (`O_EXCL | O_NOFOLLOW`), full UTC/ET observation timestamps, input prices, completed-bar end times, per-sector as-of features and initial research-only classification. There is no forward-price mark, realized profit, daily closing outcome or future label in a recorded snapshot. Later research must compute outcome separately from an independently timestamped source and must not mutate the sealed original.
- V2 experimental candidate frozen for shadow only: bearish SOXX -0.75% to -1.5% from same-day RTH open, AMD/MU/NVDA all <= -0.20% from their RTH opens, SOXX latest completed five-minute price momentum <= -0.10%. This came from exploratory earlier-selected training policy (11/18 earlier after30bp positive, 6/9 later) but is NOT reliable: nine later dates and Wilson95 lower bound ~35%. ALL other seven sector as-of features are recorded even if no provisional classification; no trade action.
- Fail-closed independently validated holiday gate using existing `holiday_gate.current_gate` with own `/var/lib/securityprepper-v2-forward-shadow/holiday_gate.json` cache. Cached rev2 unpaused until Nov13 2026 16:13 Chicago absent calendar edit. If paused/unknown, ZERO market requests and ZERO research observations. Timer can still wake to check the trusted gate; it is NOT yet incorporated in the existing owner host root DST/boundary-only DTSTART rescheduler (not necessary to stop data collection, but exact schedule deferral remains outstanding).
- Hardening: `ProtectSystem=strict`, `StateDirectory`, no capabilities, `NoNewPrivileges`, private temp/devices, bounded networking to Alpaca DATA, timeout35s.

## Validation
- **13** synthetic forward-only unit tests PASSED, including holiday pause no-network, no orders, strict prior-five distinct days, no future 5m bar inclusion, 09:35 candidate, missing peer abstain, single-write append-only seal and authenticated GET-only.
- A 21:17 CST non-scheduled service smoke test returned `NOT_SCHEDULED` with zero network requests and zero orders, and service completed with exit code 0.
- An independent authenticated GET-only Alpaca market-data smoke test (read-only one-off user `alpacafeed`) returned **23/23 symbols with at least five prior daily sessions** and **2,448 five-minute SIP price bars**; zero broker order calls.
- All inspected V1 MBB paper execution, FDR paper execution, sector monitor and semiconductor-downside warning timers remained ACTIVE after enabling the V2 shadow timer.
- The tomorrow morning forward signal has **not yet happened**, so do NOT report any true forward-only hit/miss or claim profitability based on this installation.

## Research findings prompting the installation

- Tested **1,620** early 09:35/09:45/10:05 ETF-and-peer bullish/bearish threshold/momentum/no-chase candidates for all seven sectors on 250 historic days each. Chronologically first175 TRAIN, last75 later; zero candidates met provisional >=65% after assumed 30bp 60-minute profit, positive mean, >=18 independent train signals and >=8% coverage.
- Best earlier-selected semiconductor bearish shadow: train 11/18 after30bp winners (+0.2184% mean 60m), later 6/9 (+0.8568% mean), only 9/75 later forecast days, Wilson95 lower bound ~35%. Unconditional same-time SOXX short in later portion 24/75 positive, -0.1407% average, but neither policy is guaranteed executable, and historical repeated research may introduce bias.
- Hard 1.5/2.5/4% stop stress on matched selected candidate at completed 5m close -> next bar opening proxy: semis earlier 1.5% stop triggered6/18 and reduced mean through 13:40 Chicago from +0.2146% to +0.038%; 2.5% stop triggered4/18 and changed mean to +0.234%; none of nine later trades triggered a stop, so no genuine protective validation. Gold and most others remained negative.
- All 14 synthetic historical gate/stop tests PASSED.
- Full results, code and risk journal are in `docs/RESEARCH_2026-11-09_V2_NEXT_MOVE_FIRST_AND_ANTI_CHURN_WALKFORWARD.md` and associated research scripts/JSON.

**No automatic PAPER/LIVE release is justified by these findings.**

## Next
After a new session completes, score each SEALED snapshot forward-only: side-specific movement from signal mark to next executable (or conservative delayed) entry, 15m/60m, 13:30, latest-flat 13:40 CT and next regular opening as a separate risk counterfactual; include after-cost win rate, false positives, percent abstentions, MAE/MFE, missed major up/down days and late warnings. Require >30 independent unseen days per sector/side and realistic bid/ask/short availability/commission execution evidence before considering a new directional push or broker rule.

Missing: complete synchronized historical/streaming BOATS NBBO across 20:00–04:00 ET, broker-matched V1 fill execution for all sectors, primary source prior-evening news and futures timestamps. The READ-ONLY Alpaca news observer remains separate and **does not authorize trading**.
