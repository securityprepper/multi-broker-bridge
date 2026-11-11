"""Prospective sealed, GET-only V2 sector shadow snapshots, 09:35/09:45/10:05 ET.
NO broker endpoint, alerts, orders, Pushover, position or account access.
Record observed inputs BEFORE futures/outcomes exist; never rewrite a day/slot.
"""
from __future__ import annotations
import json,os,tempfile
from hashlib import sha256
from pathlib import Path
from datetime import datetime,timezone,timedelta,time
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo
from .v2_sector_forecast_policy_20261111 import POLICY_ID, POLICY_SHA256, frozen_forecast
ET=ZoneInfo("America/New_York")
UTC=timezone.utc
BASE="https://data.alpaca.markets/v2/stocks/bars"
SECTORS={
 "semiconductors":("SOXX",("AMD","MU","NVDA")),
 "gold_miners":("GDX",("NEM","AEM","KGC")),
 "energy":("XLE",("XOM","CVX")),
 "financials":("XLF",("JPM","BAC")),
 "industrials":("XLI",("CAT","GE")),
 "healthcare":("XLV",("UNH","LLY")),
 "software":("IGV",("MSFT","CRM"))}
SLOTS=("09:35","09:45","10:05")
def parse(value):
 dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
 if dt.tzinfo is None:raise ValueError("timestamp must have zone")
 return dt.astimezone(ET)
def slot(now):
 if now.tzinfo is None:raise ValueError("time zone required")
 local=now.astimezone(ET)
 if local.weekday()>=5:return None
 for h in SLOTS:
  hh,mm=map(int,h.split(":"))
  scheduled=local.replace(hour=hh,minute=mm,second=0,microsecond=0)
  if timedelta(seconds=15)<=local-scheduled<=timedelta(seconds=90):
   return h
 return None
def symbols():
 return sorted({s for etf,peers in SECTORS.values() for s in (etf,)+peers})
def validate_daily_prior5(bars,asof):
 """Never accept any current/future daily bar as one of five prior sessions."""
 records={}
 day=asof.astimezone(ET).date()
 for s in symbols():
  rows=bars.get(s,[])
  by_day={}
  for bar in rows:
   dt=parse(bar["t"]).date()
   if dt>=day:continue
   close=float(bar["c"])
   if close<=0:continue
   if dt in by_day and by_day[dt]!=close:
    raise ValueError("conflicting daily closing bars for one date")
   by_day[dt]=close
  prior=sorted(by_day.items())
  if len(prior)<5 or (day-prior[-1][0]).days>5:
   records[s]=None
  else:
   records[s]={"five_previous_dates":[d.isoformat() for d,_ in prior[-5:]],
               "five_previous_closes":[v for _,v in prior[-5:]]}
 return records
def validate_live_bars(bars,at):
 """Keep only completed bar start +5m <= actual observation time -15s."""
 rows={}
 deadline=at.astimezone(ET)-timedelta(seconds=15)
 for s in symbols():
  v={}
  for bar in bars.get(s,[]):
   start=parse(bar["t"])
   if start+timedelta(minutes=5)>deadline:continue
   key=start.strftime("%Y-%m-%d %H:%M")
   if start.date()!=at.astimezone(ET).date():continue
   op=float(bar["o"]);hi=float(bar["h"]);lo=float(bar["l"]);cl=float(bar["c"])
   if min(op,hi,lo,cl)<=0:continue
   v[key]={"open":op,"high":hi,"low":lo,"close":cl,"bar_start_ET":start.isoformat(),
           "bar_available_after_ET":(start+timedelta(minutes=5)).isoformat()}
  rows[s]=v
 return rows
def asof_signals(now,decision,previous,live,issued_at=None):
 """Only market bars <= the current clock and prior FIVE completed daily bars."""
 etfresult={}
 issued_at=issued_at or now
 current=now.astimezone(ET).date().isoformat()
 slotdate=current+" "
 hh,mm=map(int,decision.split(":"))
 last=(now.astimezone(ET).replace(hour=hh,minute=mm,second=0,microsecond=0)-timedelta(minutes=5)).strftime("%H:%M")
 prev=(now.astimezone(ET).replace(hour=hh,minute=mm,second=0,microsecond=0)-timedelta(minutes=10)).strftime("%H:%M")
 for sector,(etf,peers) in SECTORS.items():
  names=(etf,)+peers
  metrics={}
  for s in names:
   p=previous.get(s); bars=live.get(s,{})
   opening=bars.get(slotdate+"09:30");lastbar=bars.get(slotdate+last);old=bars.get(slotdate+prev)
   if not (p and opening and lastbar and old):
    metrics={};break
   price=lastbar["close"]
   metrics[s]={"from_0930_open_pct":round(100*(price/opening["open"]-1),5),
               "last_5m_pct":round(100*(price/old["close"]-1),5),
               "observed_price":price,
               "observed_bar_end_ET":lastbar["bar_available_after_ET"]}
  # Forecast policy is exploratory and frozen BEFORE future data arrives.
  shadow=None
  if sector=="semiconductors" and metrics:
   x=metrics["SOXX"]["from_0930_open_pct"]
   m5=metrics["SOXX"]["last_5m_pct"]
   if -1.5<=x<=-.75 and m5<=-.10 and all(
     metrics[p]["from_0930_open_pct"]<=-.20 for p in ("AMD","MU","NVDA")):
    shadow="EXPLORATORY_BEARISH_SEMI_WATCH_ONLY"
  frozen=frozen_forecast(sector,etf,peers,metrics,previous,issued_at.astimezone(ET))
  etfresult[sector]={"status":"ASOF_FEATURES" if metrics else "ABSTAIN_MISSING_ASOF_DATA",
                     "features":metrics,
                     "shadow_classification":frozen["benchmark_side"],
                     "peer_confirmed_classification":frozen["peer_confirmed_side"],
                     "forward_forecast":frozen,
                     "legacy_semiconductor_watch":shadow,
                     "after_cost_predictive_alert_authorized":False,
                     "broker_order_permissions":False}
 return etfresult
def holiday_unpaused(now):
 from holiday_gate import current_gate
 p=Path(os.environ.get("V2_SHADOW_HOLIDAY_GATE",""))
 if not p.is_absolute() or not p.parent.exists():raise ValueError("missing private holiday cache")
 gate,state=current_gate(p,now)
 if gate is None:raise ValueError("unverified holiday gate")
 return gate.get("paused") is False
def fetch_bars(now,frame,cred_dir,opener=urlopen):
 if not cred_dir.is_absolute():raise ValueError("protected data credential directory required")
 key=(cred_dir/"alpaca_data_key_id").read_text().strip()
 secret=(cred_dir/"alpaca_data_secret").read_text().strip()
 if not key or not secret:raise ValueError("data credential missing")
 local=now.astimezone(ET)
 if frame=="5Min":
  start=local.replace(hour=9,minute=20,second=0,microsecond=0)
  end=now-timedelta(seconds=15)
 elif frame=="1Day":
  start=(now-timedelta(days=25))
  end=local.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(seconds=1)
 else:raise ValueError("unsupported frame")
 params={"symbols":",".join(symbols()),"timeframe":frame,"feed":"sip","adjustment":"split",
         "start":start.astimezone(UTC).isoformat(),"end":end.astimezone(UTC).isoformat(),
         "limit":10000}
 allbars={s:[] for s in symbols()}
 token=None
 for _ in range(8):
  q=dict(params)
  if token:q["page_token"]=token
  request=Request(BASE+"?"+urlencode(q),headers={"APCA-API-KEY-ID":key,
            "APCA-API-SECRET-KEY":secret,"Accept":"application/json"},method="GET")
  with opener(request,timeout=10) as response:
   if response.status!=200:raise ValueError("provider error")
   payload=json.loads(response.read(2_000_001))
  if not isinstance(payload,dict) or not isinstance(payload.get("bars"),dict):
   raise ValueError("invalid market bar payload")
  for s,b in payload["bars"].items():
   if s not in allbars or not isinstance(b,list):raise ValueError("unexpected symbol/bars")
   allbars[s].extend(b)
  token=payload.get("next_page_token")
  if not token:return allbars
  if not isinstance(token,str) or len(token)>512:raise ValueError("invalid page token")
 raise ValueError("market bars incomplete after 8 pages")
def save_once(root,now,decision,report):
 if not root.is_absolute() or not root.is_dir() or root.is_symlink():
  raise ValueError("trusted absolute state root required")
 day=now.astimezone(ET).date().isoformat()
 d=root/day
 d.mkdir(mode=0o700,exist_ok=True)
 if d.is_symlink():raise ValueError("symlink state dir rejected")
 path=d/(decision.replace(":","")+".json")
 # Exclusive creation prevents overriding an earlier sealed observation.
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  with os.fdopen(fd,"w") as f:
   json.dump(report,f,sort_keys=True)
   f.write("\n");f.flush();os.fsync(f.fileno())
 except BaseException:
  path.unlink(missing_ok=True)
  raise
 return path
def run(now=None,holiday_check=holiday_unpaused,fetch=fetch_bars,issue_clock=None):
 real_clock=(now is None)
 now=now or datetime.now(UTC)
 if now.tzinfo is None:raise ValueError("timezone required")
 decision=slot(now)
 if decision is None:
  return {"status":"NOT_SCHEDULED","orders_submitted":0,"market_data_requests":0}
 if not holiday_check(now):
  return {"status":"HOLIDAY_PAUSED_NO_POLL","orders_submitted":0,"market_data_requests":0}
 state=Path(os.environ.get("V2_SHADOW_STATE_ROOT",""))
 if not state.is_absolute() or not state.is_dir():raise ValueError("untrusted shadow root")
 path=state/now.astimezone(ET).date().isoformat()/(decision.replace(":","")+".json")
 if path.exists():
  return {"status":"ALREADY_SEALED","orders_submitted":0,"market_data_requests":0}
 creds=Path(os.environ.get("CREDENTIALS_DIRECTORY",""))
 pri=validate_daily_prior5(fetch(now,"1Day",creds),now)
 bars=validate_live_bars(fetch(now,"5Min",creds),now)
 issued_at=issue_clock() if issue_clock is not None else datetime.now(UTC) if real_clock else now
 # The true decision issuance is AFTER the final GET; do not falsely backdate to scan start.
 if issued_at.tzinfo is None or issued_at < now or slot(issued_at)!=decision:
  raise ValueError("late or inconsistent policy decision issuance")
 features=asof_signals(now,decision,pri,bars,issued_at=issued_at)
 doc={"schema_version":2,"time_of_observation_utc":now.astimezone(UTC).isoformat(),
      "time_of_observation_ET":now.astimezone(ET).isoformat(),"forecast_slot_ET":decision,
      "forecast_actual_issued_at_ET":issued_at.astimezone(ET).isoformat(),
      "forecast_policy_id":POLICY_ID,"forecast_policy_sha256":POLICY_SHA256,
      "earliest_later_entry_at_ET":(issued_at.astimezone(ET)+timedelta(minutes=5)).isoformat(),
      "source":"Alpaca SIP 5Min completed bars, GET-only",
      "no_current_or_future_outcomes_in_document":True,"research_only":True,
      "orders_submitted":0,"PAPER_orders_allowed":False,"LIVE_orders_allowed":False,
      "sectors":features}
 saved=save_once(state,now,decision,doc)
 # Seal digest is emitted to root-owned systemd journal at issuance, before outcomes.
 sealed_sha256=sha256(saved.read_bytes()).hexdigest()
 return {"status":"RESEARCH_SHADOW_SEALED","day":saved.parent.name,"slot":decision,
         "sealed_file_sha256":sealed_sha256,
         "sectors_with_asof":sum(x["status"]=="ASOF_FEATURES" for x in features.values()),
         "exploratory_semi_weakness":features["semiconductors"]["legacy_semiconductor_watch"] is not None,
         "benchmark_forecasts_issued":sum(x["shadow_classification"] in ("UP","DOWN") for x in features.values()),
         "peer_forecasts_issued":sum(x["peer_confirmed_classification"] in ("UP","DOWN") for x in features.values()),
         "orders_submitted":0,"market_data_requests":2}
if __name__=="__main__":
 try:
  print(json.dumps(run(),sort_keys=True))
 except FileExistsError:
  print(json.dumps({"status":"ALREADY_SEALED","orders_submitted":0}))
 except (OSError,TypeError,ValueError,KeyError,TimeoutError,json.JSONDecodeError) as exc:
  print(json.dumps({"status":"SHADOW_READ_ONLY_ERROR","kind":type(exc).__name__,"orders_submitted":0}))
  raise SystemExit(2)
