#!/usr/bin/env python3
"""LIVE read-only acquisition. No order write methods. Separate from PAPER."""
import base64,datetime as dt,json,os,re,subprocess,tempfile,threading,uuid
from pathlib import Path
from urllib.request import urlopen,Request
from ibapi.client import EClient
import ibapi.client as ibclient
# Negotiate the supported pre-protobuf wire format; newer negotiation stalls these account requests.
ibclient.MAX_CLIENT_VER=200
from ibapi.wrapper import EWrapper
from ibapi.execution import ExecutionFilter
UTC=dt.timezone.utc
CONFIG=Path("/etc/securityprepper-ibkr-live")
STATE=Path("/var/lib/securityprepper-ibkr-live")
URL="https://make-api-dev.securityprepper.com/trading-collector/v1/snapshot"
def send(payload):
 body=json.dumps(payload,separators=(",",":"),allow_nan=False).encode()
 with tempfile.NamedTemporaryFile(dir=STATE) as tmp:
  tmp.write(body);tmp.flush()
  signature=subprocess.check_output(["openssl","pkeyutl","-sign","-inkey",str(CONFIG/"signing.pem"),"-rawin","-in",tmp.name])
 headers={"Content-Type":"application/json","X-IBKR-Signature":base64.b64encode(signature).decode()}
 with urlopen(Request(URL,data=body,headers=headers,method="POST"),timeout=25) as r:return json.load(r)
def gate():
 with urlopen("https://securityprepper.com/.well-known/task-gate.json",timeout=10) as r:p=json.load(r)
 now=dt.datetime.now(UTC)
 def time(k):return dt.datetime.fromisoformat(p[k].replace("Z","+00:00"))
 if not(p.get("schema_version")==1 and p.get("status_valid") is True and p.get("timezone")=="America/Chicago" and p.get("calendar_coverage_ok") is True and p.get("calendar_revision") and p.get("calendar_coverage_through","")>=now.date().isoformat() and type(p.get("paused")) is bool and -60<=(now-time("published_at")).total_seconds()<=180 and time("valid_until")>now and time("next_check_at")>now):raise ValueError("HOLIDAY_UNVERIFIED")
 dropin=Path("/run/systemd/system/securityprepper-ibkr-live-collector.timer.d/80-holiday-boundary.conf")
 if p["paused"]:
  tick=time("next_check_at").astimezone(UTC)+dt.timedelta(minutes=5,seconds=1)
  dropin.parent.mkdir(parents=True,exist_ok=True);dropin.write_text("[Timer]\nOnCalendar=\nOnCalendar="+tick.strftime("%Y-%m-%d %H:%M:%S")+" UTC\n")
  subprocess.run(["systemctl","daemon-reload"],check=True);subprocess.run(["systemctl","restart","securityprepper-ibkr-live-collector.timer"],check=True)
  return False
 if dropin.exists():
  dropin.unlink();subprocess.run(["systemctl","daemon-reload"],check=True);subprocess.run(["systemctl","restart","securityprepper-ibkr-live-collector.timer"],check=True)
 return True
class App(EWrapper,EClient):
 def __init__(self):
  EClient.__init__(self,self);self.ready=threading.Event();self.account_ready=threading.Event();self.pos_end=threading.Event();self.ord_end=threading.Event();self.exec_end=threading.Event()
  self.accounts=[];self.positions={};self.orders={};self.executions={};self.failed=False;self.position_request_id=28176;self.error_codes=[]
 def placeOrder(self,*args,**kwargs):raise RuntimeError("READ_ONLY_COLLECTOR")
 cancelOrder=placeOrder
 reqGlobalCancel=placeOrder
 exerciseOptions=placeOrder
 reqAutoOpenOrders=placeOrder
 def positionMulti(self,reqId,account,modelCode,contract,qty,avgCost):
  if reqId==self.position_request_id:self.position(account,contract,qty,avgCost)
 def positionMultiEnd(self,reqId):
  if reqId==self.position_request_id:self.pos_end.set()
 def nextValidId(self,i):self.ready.set()
 def managedAccounts(self,s):self.accounts=[x for x in s.split(",") if x];self.account_ready.set()
 def error(self,*args):
  # New SDK: reqId,errorTime,code,text; old SDK: reqId,code,text.
  code=args[2] if len(args)>=4 and isinstance(args[2],int) else (args[1] if len(args)>=3 else None)
  if isinstance(code,int):self.error_codes.append(code)
  if code in (502,504,1100,1300,321,322):self.failed=True
 def position(self,account,c,qty,avgCost):
  if float(qty)==0:return
  self.positions[(account,c.conId)]={"account":account,"id":str(c.conId),"instrument":str(c.conId),"symbol":c.symbol,"asset":{"STK":"EQUITY","OPT":"OPTION","CASH":"FOREX"}.get(c.secType,c.secType),"qty":str(qty),"average_cost":avgCost,"multiplier":c.multiplier or "1","currency":c.currency}
 def positionEnd(self):self.pos_end.set()
 def openOrder(self,orderId,c,o,state):
  if state.status in ("Filled","Cancelled","ApiCancelled","Inactive"):return
  self.orders[(o.account,o.permId or orderId)]={"account":o.account,"id":str(o.permId or orderId),"instrument":str(c.conId),"symbol":c.symbol,"asset":{"STK":"EQUITY","OPT":"OPTION"}.get(c.secType,c.secType),"side":o.action,"qty":str(o.totalQuantity),"filled":str(getattr(o,"filledQuantity",0)),"status":state.status,"stop_price":o.auxPrice if o.orderType in ("STP","STP LMT","TRAIL") else None,"order_type":o.orderType,"tif":o.tif,"api_order_id":orderId,"client_id":o.clientId,"outside_rth":o.outsideRth}
 def openOrderEnd(self):self.ord_end.set()
 def execDetails(self,reqId,c,e):
  try:execution_time=parse_exec_time(e.time)
  except (ValueError,KeyError):self.failed=True;return
  self.executions[e.execId]={"account":e.acctNumber,"id":e.execId,"instrument":str(c.conId),"symbol":c.symbol,"asset":{"STK":"EQUITY","OPT":"OPTION"}.get(c.secType,c.secType),"multiplier":c.multiplier or "1","side":e.side,"qty":str(e.shares),"price":e.price,"fees":None,"time":execution_time,"order_id":str(e.permId or e.orderId)}
 def commissionAndFeesReport(self,r):
  if r.execId in self.executions:self.executions[r.execId]["fees"]=r.commissionAndFees
 def commissionReport(self,r):
  if r.execId in self.executions:self.executions[r.execId]["fees"]=r.commission
 def execDetailsEnd(self,reqId):self.exec_end.set()
def parse_exec_time(s):
 # Gateway timestamps must contain an explicit timezone, never assume host time.
 from zoneinfo import ZoneInfo
 if re.fullmatch(r"\d{8}-\d{2}:\d{2}:\d{2}",s):return dt.datetime.strptime(s,"%Y%m%d-%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
 parts=s.split()
 if len(parts)!=3:raise ValueError("EXECUTION_TIMEZONE_MISSING")
 d=dt.datetime.strptime(parts[0]+" "+parts[1],"%Y%m%d %H:%M:%S").replace(tzinfo=ZoneInfo({"US/Central":"America/Chicago","US/Eastern":"America/New_York","US/Pacific":"America/Los_Angeles","US/Mountain":"America/Denver"}.get(parts[2],parts[2])))
 return d.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")
def main():
 STATE.mkdir(parents=True,exist_ok=True)
 if not gate():print(json.dumps({"status":"HOLIDAY_PAUSED","broker_reads":0}));return
 observed=dt.datetime.now(UTC).isoformat()
 if "--transport-test" in __import__("sys").argv:
  print(json.dumps(send({"schema":1,"kind":"probe","observed_at":observed})));return
 app=App();stage="CONNECT"
 try:
  app.connect("127.0.0.1",4001,clientId=28171)
  threading.Thread(target=app.run,daemon=True).start()
  if not app.ready.wait(10) or not app.account_ready.wait(5):raise RuntimeError("GATEWAY_UNAVAILABLE")
  if len(app.accounts)!=1 or not re.fullmatch(r"U[0-9]+",app.accounts[0]):raise RuntimeError("IDENTITY_UNAVAILABLE")
  account=app.accounts[0];binding=CONFIG/"expected_account"
  if binding.exists() and binding.read_text().strip()!=account:raise RuntimeError("IDENTITY_UNAVAILABLE")
  if not binding.exists():
   fd=os.open(binding,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
   with os.fdopen(fd,"w") as h:h.write(account+"\n")
  stage="POSITIONS_SCOPED"
  app.reqPositionsMulti(app.position_request_id,account,"")
  if not app.pos_end.wait(12):raise RuntimeError("COLLECTION_FAILED")
  stage="ALL_OPEN_ORDERS"
  app.reqAllOpenOrders()
  orders_complete=app.ord_end.wait(8)
  stage="EXECUTIONS"
  execution_filter=ExecutionFilter();execution_filter.acctCode=account
  app.reqExecutions(28172,execution_filter)
  executions_complete=app.exec_end.wait(8) and not app.failed
  payload={"schema":1,"kind":"snapshot","source":"IBKR_GATEWAY_LIVE_READONLY","observed_at":dt.datetime.now(UTC).isoformat(),"api_protocol":app.serverVersion(),"run_id":"IBLIVE-"+str(uuid.uuid4()),"account":account,"positions_end":True,"orders_end":orders_complete,"executions_end":executions_complete,
    "positions":list(app.positions.values()),"orders":list(app.orders.values()) if orders_complete else [],"executions":list(app.executions.values()) if executions_complete else []}
  stage="PERSIST"
  print(json.dumps(send(payload)))
 except Exception as exc:
  status=str(exc) if str(exc) in ("GATEWAY_UNAVAILABLE","IDENTITY_UNAVAILABLE") else "COLLECTION_FAILED"
  print(json.dumps({"status":status,"health":send({"schema":1,"kind":"health","observed_at":dt.datetime.now(UTC).isoformat(),"status":status}),"orders_submitted":0,"failed_stage":stage,"position_records":len(app.positions),"error_codes":app.error_codes}))
 finally:app.disconnect()
if __name__=="__main__":main()