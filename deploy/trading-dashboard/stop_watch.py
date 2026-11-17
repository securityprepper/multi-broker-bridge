"""Report-only off-hours stop watcher. Uses scoped Percona reads and Pushover."""
import json,os,sys
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
sys.path.insert(0,"/opt/securityprepper/multi-broker-bridge")
from multi_broker_bridge.offhours_stop import detect,session,fresh,num
def watch(rows,sql,positions,quotes,now,issues):
    runs=rows("sp_robinhood_mcp_collection_runs",
        {"account":"account_id","capture":"capture_id","asof":"completed_at_utc","pc":"positions_complete","oc":"orders_complete"},
        "account_kind='AGENTIC' AND completed_at_utc IS NOT NULL ORDER BY completed_at_utc DESC")
    latest={}
    for r in runs: latest.setdefault(r["account"],r)
    orders=[]; eligible=[]; coverage=[]
    raw=rows("sp_robinhood_mcp_orders",{"account":"account_id","capture":"capture_id","id":"native_order_id",
        "symbol":"symbol","side":"side","state":"order_state","qty":"quantity","filled":"filled_quantity",
        "stop":"stop_price","asof":"observed_at_utc","payload":"payload_json"},
        "observed_at_utc>=UTC_TIMESTAMP()-INTERVAL 5 MINUTE")
    for aid,r in latest.items():
        ok=bool(r["pc"] and r["oc"] and fresh(r["asof"],now,120))
        coverage.append({"broker":"Robinhood Agentic","account":"RH:"+aid,"asof":r["asof"],"status":"CURRENT" if ok else "STALE OR INCOMPLETE — cannot verify stops"})
        if not ok: continue
        eligible.extend(p for p in positions if p["account"]=="RH:"+aid)
        for o in raw:
            if o["account"]!=aid or o["capture"]!=r["capture"]: continue
            payload=o.pop("payload")
            if isinstance(payload,str): payload=json.loads(payload)
            o.update(account="RH:"+aid,tif=payload.get("time_in_force"),paper=False)
            orders.append(o)
    ib=rows("sp_live_broker_position_order_snapshots",
        {"account":"account_id","run":"snapshot_run_id","id":"native_record_id","symbol":"symbol","side":"side",
         "state":"order_state","qty":"quantity","filled":"filled_quantity","asof":"observed_at_utc","payload":"payload_json"},
        "broker='IBKR' AND record_type='WORKING_ORDER' AND observed_at_utc>=UTC_TIMESTAMP()-INTERVAL 2 MINUTE ORDER BY observed_at_utc DESC")
    # Existing IBKR projection does not publish a complete-account manifest.
    # Never use it to authorize a trade. Matching current rows suffice only for reporting.
    for o in ib:
        payload=json.loads(o.pop("payload"))
        o.update(account="IBKR:"+o["account"],stop=payload.get("auxPrice",payload.get("stop_price")),
                 tif=payload.get("tif",payload.get("time_in_force")),paper=False)
        if o["account"].startswith("IBKR:DU"): continue
        orders.append(o)
        eligible.extend(p for p in positions if p["account"]==o["account"])
    coverage.append({"broker":"IBKR Live","status":"CURRENT MATCHED ORDER ROWS; account coverage incomplete" if ib else "UNAVAILABLE — no current Live order snapshot"})
    if not latest: coverage.append({"broker":"Robinhood Agentic","status":"UNAVAILABLE — no collection"})
    entries=detect(eligible,orders,quotes,now)
    if session(now) not in ("REGULAR","CLOSED"):
        issues.extend("Stop watch: "+c["broker"]+" "+c["status"] for c in coverage if c["status"]!="CURRENT")
    # Durable deduplication. Retry failed deliveries, don't alert every minute.
    previous=sql("SELECT JSON_OBJECT('payload',payload_json) FROM sp_offhours_stop_watch WHERE id=1;")
    old=previous[0]["payload"] if previous else {}
    if isinstance(old,str): old=json.loads(old)
    delivered=dict(old.get("delivered",{})); pending=[]
    # Re-arm only after fresh evidence of an actual recovery above this stop.
    for o in orders:
        stop=num(o.get("stop"));q=quotes.get(o.get("symbol"),{});price=num(q.get("price"))
        if stop and price and fresh(o.get("asof"),now,120) and fresh(q.get("asof"),now,90) and not q.get("stale",True) and price>=stop+max(.01,stop*.0005):
            delivered.pop(o["account"]+":"+str(o["id"])+":"+str(stop),None)
    for e in entries:
        key=e["account"]+":"+e["id"]+":"+str(e["stop"])
        if key not in delivered: pending.append((key,e))
    for start in range(0,len(pending),3):
        batch=pending[start:start+3]
        try:
            receipt=push_report([e for _,e in batch])
            for key,_ in batch: delivered[key]={"at":now.isoformat(),"request":receipt.get("request")}
        except Exception as exc: issues.append("Stop-breach Pushover pending retry: "+type(exc).__name__)
    result={"mode":"REPORT_ONLY","live_closing_enabled":False,"checked_at":now.isoformat(),"session":session(now),
        "threshold":"At least max($0.01, 0.05%) below stop","entries":entries,"coverage":coverage,"delivered":delivered,
        "paper_tests":sql("SELECT JSON_OBJECT('test',test_id,'broker',JSON_UNQUOTE(JSON_EXTRACT(payload_json,'$.broker')),'status',JSON_UNQUOTE(JSON_EXTRACT(payload_json,'$.status')),'updated',updated_at_utc) FROM sp_offhours_stop_paper_tests ORDER BY updated_at_utc DESC LIMIT 6;")}
    blob=json.dumps(result,allow_nan=False).encode().hex()
    sql("INSERT INTO sp_offhours_stop_watch (id,updated_at_utc,payload_json) VALUES (1,UTC_TIMESTAMP(6),CONVERT(0x"+blob+" USING utf8mb4)) ON DUPLICATE KEY UPDATE updated_at_utc=VALUES(updated_at_utc),payload_json=VALUES(payload_json);")
    return result


def push_report(entries,test=False,summary=None):
    from zoneinfo import ZoneInfo
    from multi_broker_bridge.offhours_stop import stamp
    ct=ZoneInfo("America/Chicago")
    text=("PAPER TEST — off-hours stop" if test else "LIVE stop breached off-hours")+"\n"
    for e in entries:
        when=stamp(e["price_asof"]).astimezone(ct).strftime("%I:%M:%S %p CT")
        text+=e["broker"]+" · "+e["symbol"]+" · acct …"+e["account"][-4:]+"\n"
        text+=str(e["qty"])+" shares · Stop $"+format(e["stop"],".2f")+" → $"+format(e["price"],".2f")+"\n"
        text+=format(e["below_pct"],".2f")+"% below · Quote "+when+"\n"
    text+=(summary if summary else "REPORT ONLY · No live order placed.")
    if len(text)>1024:raise ValueError("PUSHOVER_MESSAGE_TOO_LONG")
    base=Path(os.environ["CREDENTIALS_DIRECTORY"])
    body=urlencode({"token":(base/"pushover_token").read_text().strip(),"user":(base/"pushover_user").read_text().strip(),
        "title":"PAPER TEST: off-hours stop" if test else "Live off-hours stop breach","message":text,"priority":0 if test else 1}).encode()
    with urlopen(Request("https://api.pushover.net/1/messages.json",data=body,method="POST"),timeout=15) as r:
        receipt=json.load(r)
    if receipt.get("status")!=1:raise RuntimeError("PUSHOVER_REJECTED")
    return receipt