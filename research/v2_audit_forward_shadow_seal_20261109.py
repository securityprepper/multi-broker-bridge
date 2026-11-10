"""Read-only V2 shadow-snapshot provenance audit (no credentials, API, trades or orders).

File timestamps establish a bounded observation window, NOT cryptographic
immutability or broker execution. Missing facts fail closed.
"""
from __future__ import annotations
import argparse, hashlib, json, math, stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ET=ZoneInfo("America/New_York")
UTC=timezone.utc
EXPECTED={
 "semiconductors":("SOXX","AMD","MU","NVDA"),
 "gold_miners":("GDX","NEM","AEM","KGC"),
 "energy":("XLE","XOM","CVX"),
 "financials":("XLF","JPM","BAC"),
 "industrials":("XLI","CAT","GE"),
 "healthcare":("XLV","UNH","LLY"),
 "software":("IGV","MSFT","CRM")}
SLOTS={"09:35","09:45","10:05"}

def parse(value):
 dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
 if dt.tzinfo is None: raise ValueError("timezone missing")
 return dt.astimezone(UTC)

def numeric(v,positive=False):
 if isinstance(v,bool):raise ValueError("bool is not a numeric mark")
 x=float(v)
 if not math.isfinite(x) or positive and x<=0:raise ValueError("invalid mark")
 return x

def audit_snapshot(data,mtime,filepath=None):
 """Validate pre-outcome as-of recording and its filesystem write window."""
 errors=[]
 def fail(x):errors.append(x)
 if mtime.tzinfo is None: raise ValueError("mtime needs timezone")
 try:
  observed=parse(data["time_of_observation_utc"])
  local=parse(data["time_of_observation_ET"])
  entry=parse(data["earliest_later_entry_at_ET"])
  slot=data["forecast_slot_ET"]
  if observed!=local:fail("OBSERVATION_CLOCK_DISAGREEMENT")
  if slot not in SLOTS or observed.astimezone(ET).strftime("%H:%M")!=slot:
   fail("INVALID_SLOT_OR_OBSERVATION")
  if not 15<=observed.astimezone(ET).second<=90:fail("OBSERVATION_OUTSIDE_SLOT_WINDOW")
  if entry!=observed+timedelta(minutes=5):fail("ENTRY_CLOCK_INCONSISTENT")
  if mtime.astimezone(UTC)<observed-timedelta(seconds=2):
   fail("FILE_PRECEDES_REPORTED_OBSERVATION")
  if mtime.astimezone(UTC)>entry:fail("FILE_NOT_SEALED_BEFORE_EARLIEST_ENTRY")
  if filepath is not None:
   if filepath.name!=slot.replace(":","")+".json" or filepath.parent.name!=observed.astimezone(ET).date().isoformat():
    fail("PATH_DATE_OR_SLOT_MISMATCH")
 except (KeyError,ValueError,TypeError,AttributeError) as exc:
  return {"status":"REJECTED_FAIL_CLOSED","defects":["INVALID_CLOCK:"+type(exc).__name__],
          "cryptographically_immutable":False,"execution_verified":False}
 if data.get("schema_version")!=1:fail("UNEXPECTED_SCHEMA")
 if data.get("research_only") is not True or data.get("no_current_or_future_outcomes_in_document") is not True:
  fail("NOT_PREOUTCOME_RESEARCH")
 if data.get("orders_submitted")!=0 or data.get("PAPER_orders_allowed") is not False or data.get("LIVE_orders_allowed") is not False:
  fail("NONZERO_ORDER_PERMISSION")
 if data.get("source")!="Alpaca SIP 5Min completed bars, GET-only":
  fail("UNEXPECTED_SOURCE")
 sectors=data.get("sectors")
 if not isinstance(sectors,dict) or set(sectors)!=set(EXPECTED):
  fail("WRONG_SECTOR_UNIVERSE")
  sectors=sectors if isinstance(sectors,dict) else {}
 count=0
 watches=0
 for sector,names in EXPECTED.items():
  row=sectors.get(sector,{})
  if not isinstance(row,dict):
   fail("INVALID_SECTOR_ROW:"+sector);continue
  features=row.get("features")
  if row.get("status")=="ABSTAIN_MISSING_ASOF_DATA":
   if features!={} or row.get("shadow_classification") is not None:
    fail("ABSTENTION_HAS_FEATURES_OR_FORECAST:"+sector)
   continue
  if row.get("status")!="ASOF_FEATURES" or not isinstance(features,dict) or set(features)!=set(names):
   fail("INCOMPLETE_ASOF_SECTOR:"+sector);continue
  count+=1
  for symbol in names:
   try:
    f=features[symbol]
    end=parse(f["observed_bar_end_ET"])
    if end>observed-timedelta(seconds=15):fail("BAR_NOT_KNOWN_AT_OBSERVATION:"+symbol)
    if observed-end>timedelta(minutes=6):fail("STALE_BAR:"+symbol)
    if end.astimezone(ET).date()!=observed.astimezone(ET).date():
     fail("CROSS_DAY_BAR:"+symbol)
    numeric(f["observed_price"],positive=True)
    numeric(f["from_0930_open_pct"]);numeric(f["last_5m_pct"])
   except (KeyError,ValueError,TypeError) as exc:
    fail("INVALID_FEATURE:"+symbol+":"+type(exc).__name__)
  label=row.get("shadow_classification")
  if label is not None:
   watches+=1
   if sector!="semiconductors" or label!="EXPLORATORY_BEARISH_SEMI_WATCH_ONLY":
    fail("UNAUTHORIZED_SHADOW_LABEL:"+sector)
   else:
    try:
     soxx=features["SOXX"]
     ok=-1.5<=numeric(soxx["from_0930_open_pct"])<=-.75
     ok=ok and numeric(soxx["last_5m_pct"])<=-.10
     ok=ok and all(numeric(features[s]["from_0930_open_pct"])<=-.20 for s in ("AMD","MU","NVDA"))
     if not ok:fail("LABEL_NOT_SUPPORTED_BY_ASOF_FEATURES")
    except (KeyError,ValueError,TypeError):fail("INVALID_SHADOW_LABEL_INPUT")
 return {"status":"METADATA_WINDOW_AND_FEATURES_PASSED" if not errors else "REJECTED_FAIL_CLOSED",
         "defects":errors,"sector_features":count,"sector_abstentions":7-count,
         "shadow_watch_count":watches,"observed_at_utc":observed.isoformat(),
         "earliest_entry_at_utc":entry.isoformat(),
         "filesystem_mtime_utc":mtime.astimezone(UTC).isoformat(),
         "cryptographically_immutable":False,
         "holiday_status_reverified_by_this_auditor":False,
         "execution_verified":False,"broker_order_permissions":False}

def audit_file(path):
 if path.is_symlink() or not path.is_file():
  return {"status":"REJECTED_FAIL_CLOSED","defects":["NOT_REGULAR_NONLINK_FILE"]}
 info=path.stat()
 if not stat.S_ISREG(info.st_mode) or not 2<=info.st_size<=2000000:
  return {"status":"REJECTED_FAIL_CLOSED","defects":["BAD_FILE_TYPE_OR_SIZE"]}
 with path.open("rb") as f:raw=f.read(2000001)
 try:
  doc=json.loads(raw)
  if not isinstance(doc,dict):raise ValueError("JSON root not object")
  result=audit_snapshot(doc,datetime.fromtimestamp(info.st_mtime_ns/1e9,UTC),path)
 except (ValueError,TypeError,UnicodeDecodeError) as e:
  return {"status":"REJECTED_FAIL_CLOSED","defects":["BAD_JSON:"+type(e).__name__]}
 result["snapshot_sha256_for_reconciliation"]=hashlib.sha256(raw).hexdigest()
 result["filesystem_metadata_not_cryptographic_witness"]=True
 return result

if __name__=="__main__":
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument("snapshot_path",type=Path)
 result=audit_file(ap.parse_args().snapshot_path)
 print(json.dumps(result,sort_keys=True))
 raise SystemExit(0 if result.get("status")=="METADATA_WINDOW_AND_FEATURES_PASSED" else 2)
