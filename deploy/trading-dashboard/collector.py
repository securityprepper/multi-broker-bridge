#!/usr/bin/env python3
"""Fixed GET-only broker/market reader; Percona persistence; no order endpoints."""
import ast, concurrent.futures, datetime as dt, json, os, subprocess, sys, tempfile
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
from core import *
ROOT=Path("/opt/securityprepper/trading-dashboard")
STATE=Path("/var/lib/securityprepper-dashboard/dashboard.json")
DBCONF="/etc/securityprepper/trading-dashboard/mysql.cnf"
def sql(query):
    out=subprocess.run(["mysql","--defaults-file="+DBCONF,"--batch","--raw","--skip-column-names","securityprepper_trading"],
        input=query,text=True,capture_output=True,timeout=25)
    if out.returncode: raise RuntimeError("PERCONA_READ_FAILED")
    return [json.loads(x) for x in out.stdout.splitlines() if x]
def rows(table,fields,where="1=1"):
    # Table/column names and predicates are internal constants.
    pairs=",".join("'"+k+"',"+v for k,v in fields.items())
    return sql("SELECT JSON_OBJECT("+pairs+") FROM "+table+" WHERE "+where+";")
def api(host,path):
    if host not in ("paper-api.alpaca.markets","data.alpaca.markets"): raise ValueError("INVALID_HOST")
    if host.startswith("paper-") and not (path.startswith("/v2/positions") or path.startswith("/v2/account/activities/FILL") or path=="/v2/account"): raise ValueError("GET_NOT_ALLOWED")
    if host.startswith("data.") and not path.startswith("/v2/stocks/"): raise ValueError("GET_NOT_ALLOWED")
    cred=Path(os.environ["CREDENTIALS_DIRECTORY"])
    headers={"APCA-API-KEY-ID":(cred/"alpaca_data_key_id").read_text().strip(),
             "APCA-API-SECRET-KEY":(cred/"alpaca_data_secret").read_text().strip()}
    try:
        with urlopen(Request("https://"+host+path,headers=headers,method="GET"),timeout=20) as r: return json.load(r)
    except HTTPError as e: raise RuntimeError("HTTP_"+str(e.code)) from None
def universe():
    tree=ast.parse(Path("/opt/securityprepper/quality-opportunity-watch/quality_watch.py").read_text())
    sectors=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="SECTORS" for t in n.targets))
    mapping={s:name for name,(etf,stocks,_) in sectors.items() for s in (*stocks,etf)}
    mapping.update({s:"Semiconductors" for s in ("SOXX","SOXL","SOXS")})
    mapping.update({"GDXJ":"Gold miners","SPY":"Market","QQQ":"Market"})
    return sectors,mapping
def market(symbols,now,issues):
    local=now.astimezone(CT); feed="boats" if local.hour>=19 or local.hour<3 else "sip"
    def batch(names):
        bars={}; page=None
        for _ in range(12):
            params={"symbols":",".join(names),"timeframe":"1Min","start":(now-dt.timedelta(hours=6)).isoformat(),
                    "end":now.isoformat(),"feed":feed,"limit":10000,"sort":"asc","adjustment":"raw"}
            if page: params["page_token"]=page
            data=api("data.alpaca.markets","/v2/stocks/bars?"+urlencode(params))
            for s,items in data.get("bars",{}).items(): bars.setdefault(s,[]).extend(items)
            page=data.get("next_page_token")
            if not page: break
        if page: raise RuntimeError("BAR_HISTORY_TRUNCATED")
        snapshots=api("data.alpaca.markets","/v2/stocks/snapshots?"+urlencode({"symbols":",".join(names),"feed":"sip"}))
        result={}
        for s in names:
            snap=snapshots.get(s,{})
            prev=snap.get("prevDailyBar") or {}; daily=snap.get("dailyBar") or {}
            # Official prior settlement only; stale daily bars cannot supply today's open.
            open_price=number(daily.get("o")) if daily.get("t") and instant(daily["t"]).astimezone(CT).date()==local.date() else None
            m=movement(bars.get(s,[]),now,number(prev.get("c")),open_price)
            m["feed"]=feed.upper(); result[s]=m
        return result
    result={}
    chunks=[symbols[i:i+20] for i in range(0,len(symbols),20)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pending={pool.submit(batch,c):c for c in chunks}
        for f,c in pending.items():
            try: result.update(f.result())
            except Exception as e: issues.append("Market data "+",".join(c[:3])+": "+type(e).__name__+(" "+str(e) if isinstance(e,RuntimeError) else ""))
    return result
def publish(data):
    encoded=json.dumps(data,separators=(",",":"),allow_nan=False)
    # Hex data literal avoids SQL quoting ambiguities and preserves UTF-8.
    sql("INSERT INTO sp_dashboard_state (id,updated_at_utc,payload_json) VALUES (1,UTC_TIMESTAMP(6),CONVERT(0x"+encoded.encode().hex()+" USING utf8mb4)) ON DUPLICATE KEY UPDATE updated_at_utc=VALUES(updated_at_utc),payload_json=VALUES(payload_json);")
    STATE.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=STATE.parent,prefix=".snapshot-")
    with os.fdopen(fd,"w") as h: h.write(encoded); h.flush(); os.fsync(h.fileno())
    os.chmod(tmp,0o644); os.replace(tmp,STATE)
def main():
    now=dt.datetime.now(UTC); day=now.astimezone(CT).date().isoformat(); issues=[]
    sys.path.insert(0,"/opt/securityprepper/sector-monitor")
    from holiday_gate import validate_fresh
    try:
        gate=validate_fresh(json.loads(Path("/var/cache/securityprepper-holiday/task-gate.json").read_text()),now)
        status="HOLIDAY_PAUSED" if gate["paused"] else "UNPAUSED"
    except Exception: gate={}; status="HOLIDAY_UNVERIFIED"
    if status!="UNPAUSED":
        old=json.loads(STATE.read_text()) if STATE.exists() else {"positions":[],"closed":[],"watch":[],"accounts":[]}
        old.update({"gate":status,"next_check_at":gate.get("next_check_at"),"checked_at":now.isoformat()})
        publish(old); print(json.dumps({"gate":status,"broker_reads":0})); return
    sectors,mapping=universe(); accounts=[]; positions=[]; executions=[]
    runs=rows("sp_robinhood_mcp_collection_runs",{"account":"account_id","capture":"capture_id","kind":"account_kind","status":"status","asof":"completed_at_utc","complete":"positions_complete"},
        "completed_at_utc IS NOT NULL ORDER BY completed_at_utc DESC")
    latest={}
    for r in runs:
        if r["account"] not in latest: latest[r["account"]]=r
    for account,r in latest.items():
        aid="RH:"+account
        accounts.append({"id":aid,"label":"Robinhood "+r["kind"].title()+" · "+account[-4:],"broker":"Robinhood","paper":False,
            "asof":instant(r["asof"]).isoformat(),"status":r["status"],"complete":bool(r["complete"])})
    native=rows("sp_robinhood_mcp_positions",{"account":"account_id","capture":"capture_id","instrument":"instrument_id","symbol":"symbol","asset":"asset_class","qty":"quantity","entry":"average_cost","price":"market_price","asof":"observed_at_utc","payload":"payload_json"},
        "observed_at_utc >= UTC_TIMESTAMP()-INTERVAL 3 DAY")
    for r in native:
        if r["account"] not in latest or r["capture"]!=latest[r["account"]]["capture"]: continue
        q=number(r["qty"])
        if not q: continue
        opt=r["asset"]=="OPTION"; payload=r["payload"]
        if isinstance(payload,str): payload=json.loads(payload)
        cost=number(r["entry"]); multiplier=number(payload.get("trade_value_multiplier")) or (100 if opt else 1)
        positions.append({"id":"RH:"+r["instrument"],"account":"RH:"+r["account"],"broker":"Robinhood","paper":False,
            "symbol":r["symbol"] or r["instrument"],"instrument":r["instrument"],"asset":r["asset"],"qty":q,
            "entry":cost/multiplier if opt and cost is not None else cost,"multiplier":multiplier,
            "broker_price":number(r["price"]),"position_asof":instant(r["asof"]).isoformat(),
            "source":"Unattributed","detail":("Option · "+str(payload.get("expiration_date",""))+" · "+r["instrument"][-8:]) if opt else r["asset"]})
    rh=rows("sp_robinhood_mcp_executions",{"id":"native_execution_id","account":"account_id","instrument":"symbol","symbol":"symbol","side":"side","qty":"quantity","price":"price","fees":"fees","time":"execution_timestamp_utc"},
        "execution_timestamp_utc IS NOT NULL ORDER BY execution_timestamp_utc,id")
    seen=set()
    for r in rh:
        key=(r["account"],r["id"])
        if key in seen: continue
        seen.add(key); r.update({"account":"RH:"+r["account"],"broker":"Robinhood","paper":False,"source":"Unattributed"}); executions.append(r)
    intents=rows("sp_paper_rec_intents",{"order":"broker_order_id","source":"source_task","client":"client_order_id"},"broker_order_id IS NOT NULL")
    attribution={r["order"]:r["source"] for r in intents}
    try:
        acct=api("paper-api.alpaca.markets","/v2/account")
        expected=(Path(os.environ["CREDENTIALS_DIRECTORY"])/"expected_paper_account").read_text().strip()
        if acct.get("id")!=expected: raise RuntimeError("PAPER_ACCOUNT_ID_MISMATCH")
        aid="AP:"+acct["id"]
        ap=api("paper-api.alpaca.markets","/v2/positions")
        accounts.append({"id":aid,"label":"Alpaca PAPER · "+str(acct.get("account_number",""))[-4:],"broker":"Alpaca","paper":True,"asof":now.isoformat(),"status":"CURRENT","complete":True})
        fills=[]; page=None
        for _ in range(40):
            query={"direction":"desc","page_size":100,"after":(now-dt.timedelta(days=90)).isoformat()}
            if page: query["page_token"]=page
            batch=api("paper-api.alpaca.markets","/v2/account/activities/FILL?"+urlencode(query)); fills.extend(batch)
            if len(batch)<100: break
            page=batch[-1]["id"]
        else: issues.append("Alpaca fill history reached its page limit; unmatched entry basis stays unknown.")
        for f in fills:
            executions.append({"id":f["id"],"account":aid,"broker":"Alpaca","paper":True,"symbol":f["symbol"],"side":f["side"],
                "qty":f["qty"],"price":f["price"],"fees":None,"time":f["transaction_time"],
                "source":attribution.get(f.get("order_id"),"Unattributed")})
        for p in ap:
            source=remaining_sources(executions,aid,p["symbol"],abs(float(p["qty"])),now) if float(p["qty"])>0 else "Unattributed"
            positions.append({"id":"AP:"+p["symbol"],"account":aid,"broker":"Alpaca","paper":True,"symbol":p["symbol"],
                "instrument":p["symbol"],"asset":"EQUITY","qty":float(p["qty"]),"entry":float(p["avg_entry_price"]),
                "multiplier":1,"broker_price":number(p.get("current_price")),"position_asof":now.isoformat(),"source":source,"detail":"PAPER"})
    except Exception as e:
        issues.append("Alpaca PAPER unavailable: "+str(e) if isinstance(e,RuntimeError) else "Alpaca PAPER unavailable: "+type(e).__name__)
        accounts.append({"id":"AP:unavailable","label":"Alpaca PAPER","broker":"Alpaca","paper":True,"asof":None,"status":"UNAVAILABLE","complete":False})
    # IBKR gets an explicit coverage state; never equate a missing snapshot with cash.
    ib=rows("sp_live_broker_position_order_snapshots",{"account":"account_id","run":"snapshot_run_id","symbol":"symbol","qty":"quantity","asset":"asset_class","asof":"observed_at_utc","payload":"payload_json"},"broker='IBKR' AND record_type='POSITION' ORDER BY observed_at_utc DESC")
    if not ib:
        accounts.append({"id":"IBKR:LIVE","label":"IBKR LIVE","broker":"IBKR","paper":False,"asof":None,"status":"NO VERIFIED SNAPSHOT","complete":False})
        issues.append("IBKR LIVE: no persisted position snapshot. Its holdings and P/L are excluded.")
    else:
        ib_latest={}
        for r in ib:
            if r["account"] not in ib_latest: ib_latest[r["account"]]=r["run"]
            if r["run"]!=ib_latest[r["account"]]: continue
            aid="IBKR:"+r["account"]; payload=json.loads(r["payload"])
            if not any(a["id"]==aid for a in accounts):
                accounts.append({"id":aid,"label":"IBKR · "+r["account"][-4:],"broker":"IBKR","paper":False,"asof":instant(r["asof"]).isoformat(),"status":"SNAPSHOT ONLY","complete":False})
            if number(r["qty"]):
                positions.append({"id":aid+":"+str(r["symbol"]),"account":aid,"broker":"IBKR","paper":False,"symbol":r["symbol"],"asset":r["asset"],"qty":number(r["qty"]),"entry":number(payload.get("average_cost")),"multiplier":1,"broker_price":None,"position_asof":instant(r["asof"]).isoformat(),"source":"Unattributed","detail":"Snapshot only"})
    symbols=sorted(set(mapping)|{p["symbol"] for p in positions if p["asset"]=="EQUITY"})
    quotes=market(symbols,now,issues)
    for p in positions:
        m=quotes.get(p["symbol"],{}) if p["asset"]=="EQUITY" else {}
        p.update({"price":m.get("price"),"price_asof":m.get("asof"),"stale":m.get("stale",True),"changes":m.get("changes",{}),"sector":mapping.get(p["symbol"],"Other")})
        # Options/crypto require native instrument quotes, never the underlying equity.
        if p["price"] is None: p["price"]=p["broker_price"]
        p["pnl"]=(p["price"]-p["entry"])*p["qty"]*p["multiplier"] if p["price"] is not None and p["entry"] is not None else None
        p["pct"]=(p["price"]/p["entry"]-1)*100*(1 if p["qty"]>0 else -1) if p["price"] is not None and p["entry"] else None
    from stop_watch import watch as stop_watch
    try: stops=stop_watch(rows,sql,positions,quotes,now,issues)
    except Exception as exc:
        issues.append("Off-hours stop watch unavailable: "+type(exc).__name__)
        stops={"mode":"REPORT_ONLY","live_closing_enabled":False,"checked_at":now.isoformat(),"session":"UNKNOWN","entries":[],
               "coverage":[{"broker":"Stop watch","status":"UNAVAILABLE — collection failed; no all-clear"}]}
    closed=fifo_closed(executions,day,now)
    for c in closed:
        if c["paper"]: c["basis_status"]+="; Alpaca fees unavailable"
    watch=[dict(symbol=s,sector=mapping[s],**quotes.get(s,{"price":None,"changes":{},"stale":True,"asof":None})) for s in sorted(mapping)]
    publish({"schema":1,"generated_at":now.isoformat(),"checked_at":now.isoformat(),"day":day,"timezone":"America/Chicago","gate":status,
        "next_check_at":gate["next_check_at"],"stop_watch":stops,"accounts":accounts,"positions":positions,"closed":closed,"watch":watch,"issues":issues,
        "notes":["Prices use completed one-minute traded bars; each quote shows its own time.","Day change is versus prior settlement; Open is versus today's regular-session open.","Totals include priced records only. Stale and missing prices are flagged.","Robinhood execution history is provider-partial. Closed P/L uses matched long FIFO lots only.","Alpaca closed P/L excludes unavailable fees. Sources require order-ID linkage; otherwise Unattributed."]})
    print(json.dumps({"published":True,"positions":len(positions),"closed":len(closed),"watch":len(watch),"issues":len(issues),"orders_submitted":0}))
if __name__=="__main__": main()