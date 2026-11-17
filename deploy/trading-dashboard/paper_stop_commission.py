"""One-share Alpaca PAPER off-hours stop commissioning; never live."""
import sys,json,os,time,uuid
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path[:0]=["/opt/securityprepper/direction-paper-executor","/opt/securityprepper/multi-broker-bridge","/opt/securityprepper/trading-dashboard"]
from direction_paper import trusted_gate,quote_snapshot,asset_check
from multi_broker_bridge.offhours_stop import detect,paper_exit_plan,session
from collector import sql
UTC=timezone.utc
base=Path(os.environ["CREDENTIALS_DIRECTORY"])
headers={"APCA-API-KEY-ID":(base/"alpaca_data_key_id").read_text().strip(),"APCA-API-SECRET-KEY":(base/"alpaca_data_secret").read_text().strip()}
prefix="OSW-"+uuid.uuid4().hex[:15]; evidence={"test":prefix,"broker":"Alpaca PAPER","live_orders":0,"steps":[]}
def api(method,path,body=None):
 if trusted_gate(datetime.now(UTC)):raise RuntimeError("HOLIDAY_PAUSED")
 if not path.startswith("/v2/"):raise ValueError("PATH")
 req=Request("https://paper-api.alpaca.markets"+path,headers=headers,method=method,data=json.dumps(body).encode() if body is not None else None)
 req.add_header("Content-Type","application/json")
 try:
  with urlopen(req,timeout=15) as r:return json.load(r) if r.status!=204 else None
 except HTTPError as e:raise RuntimeError("PAPER_HTTP_"+str(e.code)+":"+e.read(600).decode()) from None
def record(stage,**kw):
 evidence["steps"].append(dict(stage=stage,at=datetime.now(UTC).isoformat(),**kw))
 print(json.dumps(evidence["steps"][-1]),flush=True)
def wait(oid,states,seconds=25):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  o=api("GET","/v2/orders/"+oid)
  if o["status"] in states:return o
  if o["status"] in ("rejected","expired","canceled") and o["status"] not in states:raise RuntimeError("ORDER_"+o["status"])
  time.sleep(1)
 raise RuntimeError("WAIT_TIMEOUT_"+o["status"])
def persist():
 blob=json.dumps(evidence,allow_nan=False).encode().hex()
 sql("INSERT INTO sp_offhours_stop_paper_tests(test_id,updated_at_utc,payload_json) VALUES ('"+prefix+"',UTC_TIMESTAMP(6),CONVERT(0x"+blob+" USING utf8mb4)) ON DUPLICATE KEY UPDATE updated_at_utc=VALUES(updated_at_utc),payload_json=VALUES(payload_json);")
 Path("/var/lib/securityprepper-dashboard/"+prefix+".json").write_text(json.dumps(evidence,indent=2))
def main():
 acct=api("GET","/v2/account")
 if acct["id"]!=(base/"expected_paper_account").read_text().strip():raise RuntimeError("ACCOUNT_MISMATCH")
 if session(datetime.now(UTC)) in ("REGULAR","CLOSED"):raise RuntimeError("OFFHOURS_REQUIRED")
 positions=api("GET","/v2/positions");orders=api("GET","/v2/orders?status=open&limit=500")
 if os.environ.get("RESUME_BUY"):
  for prior in orders:
   if prior["symbol"]=="SPY" and prior["client_order_id"].startswith("OSW-") and prior["side"]=="sell":
    api("DELETE","/v2/orders/"+prior["id"]);wait(prior["id"],{"canceled","filled"});record("PRIOR_TEST_STOP_RECONCILED",id=prior["id"])
  positions=api("GET","/v2/positions");orders=api("GET","/v2/orders?status=open&limit=500")
 if len(orders)>=500:raise RuntimeError("INCOMPLETE_ORDERS")
 busy={x["symbol"] for x in positions+orders}
 sym=next((s for s in ("SPY","QQQ","IWM","DIA") if s not in busy),None)
 if not sym:raise RuntimeError("NO_ISOLATED_TEST_SYMBOL")
 asset=api("GET","/v2/assets/"+sym)
 if not asset.get("tradable") or "overnight_tradable" not in asset.get("attributes",[]) or "overnight_halted" in asset.get("attributes",[]):raise RuntimeError("OVERNIGHT_ASSET_GUARD")
 q=quote_snapshot(sym,datetime.now(UTC))
 ask=float(q["ask"]);bid=float(q["bid"])
 if ask>1900 or (datetime.now(UTC)-q["time"]).total_seconds()>15:raise RuntimeError("QUOTE_OR_NOTIONAL_GUARD")
 resume=os.environ.get("RESUME_BUY")
 if resume:
  buy=api("GET","/v2/orders/"+resume)
  if buy["symbol"]!="SPY" or not buy["client_order_id"].startswith("OSW-") or buy["side"]!="buy" or buy["status"]!="filled" or float(buy["filled_qty"])!=1:raise RuntimeError("RESUME_IDENTITY_GUARD")
  sym="SPY"
  current=next((p for p in positions if p["symbol"]==sym),None)
  if not current or float(current["qty"])!=1 or any(o["symbol"]==sym for o in orders):raise RuntimeError("RESUME_INVENTORY_GUARD")
 else:
  buy=api("POST","/v2/orders",dict(symbol=sym,side="buy",qty="1",type="limit",time_in_force="day",extended_hours=True,limit_price=str(round(ask*1.001,2)),client_order_id=prefix+"-buy"))
  record("BUY_SUBMITTED",symbol=sym,id=buy["id"])
  try:buy=wait(buy["id"],{"filled"})
  except Exception:
   api("DELETE","/v2/orders/"+buy["id"]);raise
 record("BUY_FILLED",id=buy["id"],qty=buy["filled_qty"],price=buy["filled_avg_price"])
 q=quote_snapshot(sym,datetime.now(UTC));bid=float(q["bid"])
 stopprice=round(bid*1.003,2)
 try:
  stop=api("POST","/v2/orders",dict(symbol=sym,side="sell",qty="1",type="stop",time_in_force="gtc",stop_price=str(stopprice),client_order_id=prefix+"-stop"))
 except RuntimeError as e:
  # Broker validates against its own market price. Use its returned cap only.
  if "stop price must be less" not in str(e):raise
  detail=json.loads(str(e).split(":",1)[1]);stopprice=round(float(detail["market_price"])-.02,2)
  q=quote_snapshot(sym,datetime.now(UTC));bid=float(q["bid"])
  if stopprice-bid<max(.01,stopprice*.0005):raise RuntimeError("NO_NATURAL_OFFHOURS_BREACH")
  stop=api("POST","/v2/orders",dict(symbol=sym,side="sell",qty="1",type="stop",time_in_force="gtc",stop_price=str(stopprice),client_order_id=prefix+"-stop2"))
 record("GTC_STOP_SUBMITTED",id=stop["id"],stop=stopprice)
 stop=wait(stop["id"],{"new","accepted","held","pending_new"})
 time.sleep(2);stop=api("GET","/v2/orders/"+stop["id"])
 if float(stop["filled_qty"])!=0:raise RuntimeError("STOP_UNEXPECTED_FILL")
 q=quote_snapshot(sym,datetime.now(UTC));now=datetime.now(UTC);bid=float(q["bid"])
 # Isolated normalized paper fixture exercises the same production detector.
 p=dict(account="PAPER_TEST",broker="Alpaca PAPER TEST",paper=False,asset="EQUITY",symbol=sym,qty=1,position_asof=now.isoformat())
 o=dict(account="PAPER_TEST",id=stop["id"],symbol=sym,side="sell",state=stop["status"],tif=stop["time_in_force"],stop=stopprice,qty=1,filled=0,asof=now.isoformat())
 found=detect([p],[o],{sym:dict(price=bid,asof=q["time"].isoformat(),stale=False)},now)
 if not found:raise RuntimeError("BREACH_NOT_DETECTED")
 record("BREACH_DETECTED_STOP_UNFILLED",entry=found[0])
 api("DELETE","/v2/orders/"+stop["id"])
 terminal=wait(stop["id"],{"canceled","filled"})
 record("STOP_TERMINAL",status=terminal["status"],filled=terminal["filled_qty"])
 pos=api("GET","/v2/positions")
 remaining=next((float(x["qty"]) for x in pos if x["symbol"]==sym),0)
 if remaining>0:
  q=quote_snapshot(sym,datetime.now(UTC));now=datetime.now(UTC)
  plan=paper_exit_plan("ALPACA_PAPER:"+acct["id"],remaining,1,float(terminal["filled_qty"]),float(q["bid"]),q["time"],now,True)
  plan.pop("session");plan.pop("live_enabled");plan.update(symbol=sym,client_order_id=prefix+"-exit")
  exit=api("POST","/v2/orders",plan);record("EXIT_SUBMITTED",id=exit["id"],plan=plan)
  exit=wait(exit["id"],{"filled"});record("EXIT_FILLED",id=exit["id"],qty=exit["filled_qty"],price=exit["filled_avg_price"])
 final=api("GET","/v2/positions");record("POSITION_READBACK",test_symbol_qty=next((x["qty"] for x in final if x["symbol"]==sym),"0"))
 evidence["status"]="PASS"
if __name__=="__main__":
 try:main()
 except Exception as e:evidence["status"]="INCOMPLETE";record("ERROR",error=str(e))
 finally:persist()