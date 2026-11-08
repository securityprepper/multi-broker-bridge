import json,datetime as dt,collections,statistics
from zoneinfo import ZoneInfo
E=ZoneInfo('America/New_York'); D=dt.datetime; T=dt.timedelta
allraw=json.load(open('/tmp/semis_52wk_5min_sip_adjusted.json'))
allraw.update(json.load(open('/tmp/semis_peers_52wk_5min_adjusted.json')))
daily=json.load(open('/tmp/semis_52weeks_alpaca_daily.json'))['split']
calendar=sorted(set.intersection(*(set(x[0][:10] for x in daily[s]) for s in ('AMD','MU','SNDK','SOXX'))))
raw={}
for s,rows in allraw.items():
 raw[s]={D.fromisoformat(t.replace('Z','+00:00')).astimezone(E).replace(second=0,microsecond=0):b for t,b in rows.items()}
closes={}
for s,rs in raw.items():
 close={}
 for t,b in rs.items():
  if t.hour==15 and t.minute==55:close[str(t.date())]=b[3]
 closes[s]=close
observations=[]
for i,day in enumerate(calendar):
 if i==0:continue
 prior=calendar[i-1]
 for s in sorted(raw):
  data=raw[s];cl=closes[s]
  if day not in cl or prior not in cl:continue
  loss=cl[day]/cl[prior]-1<=-.05
  target=dt.date.fromisoformat(day)
  matches={}
  times=sorted(t for t in data if ((t.date()==target and (t.hour<9 or (t.hour==9 and t.minute<=15)) and t.hour>=4) or
                                   (t.date()==target-T(days=1) and 16<=t.hour<20)))
  for threshold,mom in ((.005,.002),(.01,.003),(.02,.005)):
   signal=None
   for t in times:
    prev=data.get(t-T(minutes=15))
    if not prev:continue
    b=data[t]
    # Only completed 5m bars; timestamp reported as interval end.
    if b[3]/cl[prior]-1<=-threshold and b[3]/prev[3]-1<=-mom:
     signal=t+T(minutes=5);break
   matches[(threshold,mom)]=signal
  observations.append((day,s,loss,matches))
print('SINGLE_STOCK_EVENTS_EVALUABLE',len(observations),'TOTAL_5PCT_DECLINES',sum(x[2] for x in observations),'ANY_STOCK_DECLINE_DAYS',len({x[0] for x in observations if x[2]}))
for threshold,mom in ((.005,.002),(.01,.003),(.02,.005)):
 good=[x for x in observations if x[2]]
 flagged=[x for x in observations if x[3][threshold,mom] is not None]
 caught=[x for x in flagged if x[2]]
 separate={d for d,s,loss,_ in caught}
 print('STOCK_SIGNAL',threshold,mom,'FLAGGED_STOCK_DAYS',len(flagged),'HIT_BIG_5PCT_STOCK_DAYS',len(caught),'RECALL',round(100*len(caught)/len(good),1),'PRECISION',round(100*len(caught)/len(flagged),1) if flagged else None,'DAYS_ANY_WARNING',len({x[0] for x in flagged}),'DAYS_ANY_BIG_DECLINE_CAUGHT',len(separate))
 print('HIT_TIMES',dict(collections.Counter('evening' if x[3][threshold,mom].date().isoformat()!=x[0] else 'premarket' for x in caught)))
 for s in ('AMD','MU','SNDK','WDC','INTC','NVDA'):
  a=[x for x in good if x[1]==s];b=[x for x in caught if x[1]==s]
  print('  STOCK',s,'HIT',len(b),'OF',len(a))
print('NEGATIVE_STOCK_DAYS_MISSED_AT_THRESHOLD_0_005',[(day,s) for day,s,loss,hit in observations if loss and hit[.005,.002] is None][:45])
