#!/usr/bin/env python3
"""RESEARCH ONLY: isolated, checkpointed 2-year 1-minute Alpaca historical
SIP premarket, BOATS overnight and missing RTH; plus final Nov20 RTH.
No broker orders or active configuration changes. Split-adjusted bars.
"""
import ast, concurrent.futures, csv, datetime as dt, gzip, hashlib, json, os, random, sys, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from zoneinfo import ZoneInfo
UTC=dt.timezone.utc;CT=ZoneInfo("America/Chicago")
ROOT=Path("/var/lib/securityprepper-two-year-early-session-research")
ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
SOURCE=Path("/var/lib/securityprepper-two-year-sector-backtest")
PRIORITY=Path("/opt/securityprepper/quality-opportunity-watch/priority_universe.json")
src=json.loads((SOURCE/"full_membership_frozen.json").read_text())
priority=json.loads(PRIORITY.read_text())
base=set(src["symbols"])
additional={s for group in priority["groups"].values() for s in group}
symbols=sorted(base|additional|{"SPY","SOXX","IGV","SOXL"})
rth_missing=sorted({s for s in symbols if not (SOURCE/"sip1m"/(s+".csv.gz")).is_file()})
rth_nov20=symbols
start="2024-11-20T00:00:00Z"
end="2026-11-21T02:00:00Z"
jobs=[("SIP_PRE",s,start,end) for s in symbols]+[("BOATS_NIGHT",s,start,end) for s in symbols]+[("SIP_RTH_NEW",s,start,"2026-11-20T00:00:00Z") for s in rth_missing]+[("SIP_RTH_NOV20",s,"2026-11-20T00:00:00Z",end) for s in rth_nov20]
configuration={
"schema":1,"source":"Alpaca historical SIP and BOATS, GET-only",
"symbol_count":len(symbols),"symbols":symbols,"rth_missing":rth_missing,
"feeds":["sip","boats"],"adjustment":"split",
"start":start,"end":end,"jobs":len(jobs),
"universe_provenance":"Existing frozen 223-sector member universe plus priority universe and reference ETFs, not point-in-time historical membership",
"priority_sha256":hashlib.sha256(PRIORITY.read_bytes()).hexdigest(),
"frozen_sha256":hashlib.sha256((SOURCE/"full_membership_frozen.json").read_bytes()).hexdigest()
}
cfg=ROOT/"manifest_config.json"
if cfg.exists():
 assert json.loads(cfg.read_text())==configuration, "FROZEN_CONFIG_MISMATCH"
else:
 cfg.write_text(json.dumps(configuration,indent=2))
c=Path("/etc/securityprepper/alpaca-feed/private")
headers={"APCA-API-KEY-ID":(c/"alpaca_data_key_id").read_text().strip(),"APCA-API-SECRET-KEY":(c/"alpaca_data_secret").read_text().strip()}
GATE=Path("/var/cache/securityprepper-holiday/task-gate.json")
def ts(x):
 t=dt.datetime.fromisoformat(str(x).replace("Z","+00:00"))
 if t.tzinfo is None:raise ValueError("TZ_MISSING")
 return t.astimezone(UTC)
def authorized():
 j=json.loads(GATE.read_text());n=dt.datetime.now(UTC)
 if not (j.get("schema_version")==1 and j.get("status_valid") is True and j.get("calendar_coverage_ok") is True and j.get("timezone")=="America/Chicago" and j.get("paused") is False and ts(j["published_at"])<=n<ts(j["valid_until"]) and n<ts(j["next_check_at"])):
  raise RuntimeError("FRESH_HOLIDAY_GATE_NOT_UNPAUSED")
 return True
def getpage(sym,feed,start,end,token):
 a={"symbols":sym,"timeframe":"1Min","start":start,"end":end,"feed":feed,"adjustment":"split","limit":10000,"sort":"asc"}
 if token:a["page_token"]=token
 u="https://data.alpaca.markets/v2/stocks/bars?"+urlencode(a)
 for attempt in range(6):
  try:
   with urlopen(Request(u,headers=headers,method="GET"),timeout=32) as resp:
    d=json.load(resp)
   if not isinstance(d.get("bars"),dict):raise ValueError("MALFORMED_RESPONSE")
   return d
  except (HTTPError,OSError,ValueError) as e:
   if attempt>=5:raise
   time.sleep(min(15,0.75*2**attempt)+random.random()/3)
def qualifies(stamp,mode):
 local=stamp.astimezone(CT)
 day=local.date()
 if day<dt.date(2024,11,20) or day>dt.date(2026,11,20):return False
 if local.weekday()>4:return False
 t=local.time()
 if mode=="SIP_PRE":return dt.time(0)<=t<dt.time(8,30)
 if mode=="BOATS_NIGHT":return dt.time(0)<=t<dt.time(8,30)
 if mode in ("SIP_RTH_NEW","SIP_RTH_NOV20"):
  return dt.time(8,30)<=t<dt.time(15) and (mode=="SIP_RTH_NEW" or day==dt.date(2026,11,20))
 raise ValueError(mode)
def job(item):
 mode,sym,start,end=item
 d=ROOT/mode; d.mkdir(parents=True,exist_ok=True,mode=0o700)
 out=d/(sym+".csv.gz"); meta=d/(sym+".meta.json")
 if out.is_file() and meta.is_file():
  j=json.loads(meta.read_text())
  if j.get("status")=="COMPLETE" and j.get("source_symbol")==sym and j.get("start")==start and j.get("end")==end and j.get("adjustment")=="split" and out.stat().st_size>20:
   return {"symbol":sym,"mode":mode,"rows":j["rows"],"cached":True,"pages":j["pages"]}
 authorized()
 page=0;token=None;first=None;last=None;duplicates=0;count=0;byday=set();seen=set()
 tmp=out.with_suffix(".tmp.gz")
 try:
  with gzip.open(tmp,"wt",compresslevel=3,newline="") as f:
   w=csv.writer(f)
   while page<165:
    if page%7==0:authorized()
    data=getpage(sym,"boats" if mode=="BOATS_NIGHT" else "sip",start,end,token)
    page+=1
    rows=data["bars"].get(sym,[])
    for r in rows:
     t=r.get("t")
     if not t:continue
     if last is not None and t<=last:
      if t==last: duplicates+=1;continue
      raise RuntimeError("NONMONOTONIC_VENDOR_TIMES")
     last=t; first=first or t
     stamp=ts(t)
     if not qualifies(stamp,mode):continue
     vol=float(r.get("v") or 0)
     if vol<=0:continue
     key=int(stamp.timestamp()//60)
     if key in seen:duplicates+=1;continue
     seen.add(key)
     w.writerow((key,r["o"],r["h"],r["l"],r["c"],r["v"]))
     count+=1;byday.add(str(stamp.astimezone(CT).date()))
    token=data.get("next_page_token")
    if not token:break
   else:
    raise RuntimeError("PAGINATION_165PAGE_MAX")
  m={"status":"COMPLETE","source_symbol":sym,"mode":mode,"rows":count,"pages":page,"start":start,"end":end,"feed":"boats" if mode=="BOATS_NIGHT" else "sip","adjustment":"split","duplicates":duplicates,"days_with_trades":len(byday),"source_first":first,"source_last":last}
  md=meta.with_suffix(".meta.tmp");md.write_text(json.dumps(m,sort_keys=True))
  os.replace(tmp,out);os.replace(md,meta)
  return {"symbol":sym,"mode":mode,"rows":count,"pages":page,"cached":False}
 finally:
  if tmp.exists():tmp.unlink()
def main():
 authorized()
 print("START",dt.datetime.now(UTC).isoformat(),"symbols",len(symbols),"missing_RTH",len(rth_missing),"jobs",len(jobs),flush=True)
 failed={};completed=[];modes={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=14) as ex:
  futures={ex.submit(job,j):j for j in jobs}
  for i,f in enumerate(concurrent.futures.as_completed(futures),1):
   j=futures[f]
   try:r=f.result();completed.append(r);modes[r["mode"]]=modes.get(r["mode"],0)+1
   except Exception as e:
    failed[f"{j[0]}:{j[1]}"]=type(e).__name__+":"+str(e)[:160]
   if i%20==0 or i==len(jobs):
    print("PROGRESS",i,len(jobs),"completed",len(completed),"failed",len(failed),"rows",sum(r["rows"] for r in completed),"pages",sum(r["pages"] for r in completed),"mode",modes,flush=True)
 report={"status":"COMPLETE" if not failed else "INCOMPLETE","symbol_count":len(symbols),"jobs":len(jobs),"completed":len(completed),"failed":failed,"modes":modes,"rows":sum(r["rows"] for r in completed),"pages":sum(r["pages"] for r in completed),"asof":dt.datetime.now(UTC).isoformat()}
 (ROOT/"download_result.json").write_text(json.dumps(report,indent=2,sort_keys=True))
 print("FINISHED",json.dumps(report,sort_keys=True),flush=True)
if __name__=="__main__":main()