"""One-share IBKR PAPER off-hours stop test; fixed DU account and local port 4002."""
import threading,time,json,uuid,sys,os
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from offhours_stop import detect,paper_exit_plan,stamp,session
UTC=timezone.utc
EXPECTED=os.environ.get("IBKR_EXPECTED_PAPER_ACCOUNT","");ref="OSW-"+uuid.uuid4().hex[:12]
evidence={"test":ref,"broker":"IBKR PAPER","live_orders":0,"steps":[]}
def record(stage,**kw):
 evidence["steps"].append(dict(stage=stage,at=datetime.now(UTC).isoformat(),**kw));print(json.dumps(evidence["steps"][-1]),flush=True)
def gate():
 d=json.loads(Path("/opt/ibkr-bridge/offhours-test-gate.json").read_text());now=datetime.now(UTC)
 if d.get("paused") is not False or d.get("status_valid") is not True or not stamp(d["published_at"])<=now<stamp(d["valid_until"]):raise RuntimeError("HOLIDAY_GATE_STALE_OR_PAUSED")
class App(EWrapper,EClient):
 def __init__(self):
  EClient.__init__(self,self);self.ready=threading.Event();self.pe=threading.Event();self.oe=threading.Event();self.accounts=[];self.positions={};self.orders={};self.states={};self.quotes={};self.errors=[]
 def nextValidId(self,i):self.oid=i;self.ready.set()
 def managedAccounts(self,s):self.accounts=s.split(",")
 def error(self,reqId,*args):
  if len(args)>=3 and isinstance(args[1],int):code,msg=args[1],args[2]
  else:code,msg=args[0],args[1]
  if code not in (2104,2106,2107,2108,2158,2119):self.errors.append([reqId,code,str(msg)[:500]])
 def position(self,a,c,q,cost):
  if a==EXPECTED:self.positions[c.symbol]=float(q)
 def positionEnd(self):self.pe.set()
 def openOrder(self,i,c,o,s):self.orders[i]=dict(symbol=c.symbol,ref=o.orderRef,type=o.orderType,status=s.status);self.states.setdefault(i,dict(status=s.status,filled=0,remaining=float(o.totalQuantity),price=0))
 def openOrderEnd(self):self.oe.set()
 def orderStatus(self,i,status,filled,remaining,avgFillPrice,*args):self.states[i]=dict(status=status,filled=float(filled),remaining=float(remaining),price=avgFillPrice)
 def tickPrice(self,r,t,p,a):
  if t in (1,2) and p>0:self.quotes[t]=(p,datetime.now(UTC))
 def send(self,c,side,kind,qty,price,ref_suffix,tif="DAY",outside=True):
  gate()
  if self.accounts!=[EXPECTED] or not EXPECTED.startswith("DU"):raise RuntimeError("PAPER_IDENTITY")
  if not 0<qty<=1 or price*qty>2000:raise RuntimeError("SIZE_GUARD")
  o=Order();o.account=EXPECTED;o.action=side;o.orderType=kind;o.totalQuantity=Decimal(str(qty));o.tif=tif;o.outsideRth=outside;o.orderRef=ref+ref_suffix;o.transmit=True
  if kind=="LMT":o.lmtPrice=price
  elif kind=="STP":o.auxPrice=price
  else:raise RuntimeError("ORDER_TYPE")
  oid=self.oid;self.oid+=1;self.placeOrder(oid,c,o);record("ORDER_SUBMITTED",id=oid,side=side,type=kind,price=price,exchange=c.exchange,tif=tif)
  return oid
 def inventory(self):
  self.pe.clear();self.oe.clear();self.positions={};self.orders={}
  self.reqPositions();self.reqAllOpenOrders()
  if not self.pe.wait(10) or not self.oe.wait(10):raise RuntimeError("INVENTORY_INCOMPLETE")
  self.cancelPositions()
 def wait(self,oid,states,seconds=20):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   s=self.states.get(oid,{})
   if s.get("status") in states:return s
   if any(x[0]==oid and x[1] not in (202,399,2109) for x in self.errors):raise RuntimeError("BROKER_ERROR_"+str(self.errors))
   time.sleep(.25)
  raise RuntimeError("ORDER_TIMEOUT_"+str(self.states.get(oid))+" "+str(self.errors))
def main():
 gate()
 a=App();a.connect("127.0.0.1",4002,179);threading.Thread(target=a.run,daemon=True).start()
 try:
  if not a.ready.wait(10):raise RuntimeError("GATEWAY_TIMEOUT")
  if a.accounts!=[EXPECTED]:raise RuntimeError("ACCOUNT_IDENTITY")
  trading_session=session(datetime.now(UTC))
  if trading_session not in ("OVERNIGHT","PREMARKET","AFTERHOURS"):raise RuntimeError("OFFHOURS_TEST_REQUIRED")
  a.inventory()
  if a.positions.get("SPY",0)!=0 or any(o["symbol"]=="SPY" for o in a.orders.values()):raise RuntimeError("EXISTING_SPY_EXPOSURE")
  c=Contract();c.symbol="SPY";c.secType="STK";c.currency="USD";c.exchange="OVERNIGHT" if trading_session=="OVERNIGHT" else "SMART"
  a.reqMktData(1791,c,"",False,False,[])
  end=time.monotonic()+10
  while time.monotonic()<end and not (1 in a.quotes and 2 in a.quotes):time.sleep(.2)
  if not (1 in a.quotes and 2 in a.quotes):raise RuntimeError("NO_OVERNIGHT_QUOTE")
  bid,bt=a.quotes[1];ask,at=a.quotes[2]
  if bid>ask or (ask-bid)/ask>.005 or (datetime.now(UTC)-min(bt,at)).total_seconds()>15:raise RuntimeError("QUOTE_GUARD")
  buy=a.send(c,"BUY","LMT",1,round(ask*1.001,2),"-buy")
  fill=a.wait(buy,{"Filled"});record("BUY_FILLED",id=buy,**fill)
  a.inventory()
  if a.positions.get("SPY")!=1:raise RuntimeError("POSITION_NOT_ONE")
  stopc=Contract();stopc.symbol="SPY";stopc.secType="STK";stopc.currency="USD";stopc.exchange="SMART"
  bid,bt=a.quotes[1];stopprice=round(bid*1.003,2)
  stop=a.send(stopc,"SELL","STP",1,stopprice,"-stop",tif="GTC",outside=False)
  state=a.wait(stop,{"PreSubmitted","Submitted","PendingSubmit"})
  time.sleep(2);state=a.states[stop]
  if state["filled"]!=0:raise RuntimeError("STOP_UNEXPECTED_FILL")
  now=datetime.now(UTC);bid,bt=a.quotes[1]
  found=detect([dict(account="PAPER_TEST",symbol="SPY",asset="EQUITY",qty=1,paper=False,broker="IBKR PAPER TEST",position_asof=now.isoformat())],
    [dict(account="PAPER_TEST",symbol="SPY",id=str(stop),side="sell",state=state["status"],tif="GTC",stop=stopprice,qty=1,filled=state["filled"],asof=now.isoformat())],
    {"SPY":dict(price=bid,asof=bt.isoformat(),stale=False)},now)
  if not found:raise RuntimeError("BREACH_NOT_DETECTED")
  record("BREACH_DETECTED_STOP_UNFILLED",entry=found[0])
  gate();a.cancelOrder(stop,"")
  terminal=a.wait(stop,{"Cancelled","ApiCancelled","Filled"});record("STOP_TERMINAL",**terminal)
  a.inventory();remaining=a.positions.get("SPY",0)
  if remaining>0:
   bid,bt=a.quotes[1];now=datetime.now(UTC)
   plan=paper_exit_plan(EXPECTED,remaining,1,terminal["filled"],bid,bt,now,True)
   exit=a.send(c,"SELL","LMT",plan["qty"],plan["limit_price"],"-exit")
   filled=a.wait(exit,{"Filled"});record("EXIT_FILLED",id=exit,**filled)
  a.inventory();record("POSITION_READBACK",test_symbol_qty=a.positions.get("SPY",0))
  if a.positions.get("SPY",0)!=0:raise RuntimeError("POSITION_REMAINS")
  evidence["status"]="PASS"
 finally:
  evidence["broker_errors"]=a.errors
  evidence["order_states"]=a.states
  evidence["open_orders"]=a.orders
  evidence["positions"]=a.positions
  a.disconnect()
if __name__=="__main__":
 try:main()
 except Exception as e:evidence["status"]="INCOMPLETE";record("ERROR",error=str(e))
 finally:
  Path("/opt/ibkr-bridge/"+ref+".json").write_text(json.dumps(evidence,indent=2))