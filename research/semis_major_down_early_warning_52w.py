import sys,datetime as dt,collections,statistics,math
sys.path.insert(0,'/tmp')
from semis_year_intraday_chronological import daily_map,calendar,stream,S,LEAD,E,D,T,bydate

label={};reasons={};stats={}
for i,day in enumerate(calendar):
 if i==0:continue
 prior=calendar[i-1]
 r={s:daily_map[s][day][4]/daily_map[s][prior][4]-1 for s in S}
 ndown=sum(r[s]<0 for s in LEAD);nup=sum(r[s]>0 for s in LEAD)
 direction='down' if ndown>=2 and r['SOXX']<0 else 'up' if nup>=2 and r['SOXX']>0 else 'mixed'
 severe='soxx5' if r['SOXX']<=-.05 else 'leaders5' if sum(r[s]<=-.05 for s in LEAD)>=2 else 'other'
 label[day]=(direction,severe,r)
print('SESSIONS',len(calendar),'EVALUATED',len(label),'DIRECTION',dict(collections.Counter(x[0] for x in label.values())))
print('5PCT_SOVERE',dict(collections.Counter(x[1] for x in label.values())), 'SOXX_DOWN_AT_LEAST_5',sum(x[2]['SOXX']<=-.05 for x in label.values()),'TWO_LEADERS_DOWN_AT_LEAST_5',sum(sum(x[2][s]<=-.05 for s in LEAD)>=2 for x in label.values()))
major={day for day,(_,_,r) in label.items() if r['SOXX']<=-.05 or sum(r[s]<=-.05 for s in LEAD)>=2}
print('UNIQUE_MAJOR_DAYS',len(major),'PERCENT',round(len(major)/len(label)*100,1))
print('MAJOR_DATES',[(d,round(label[d][2]['SOXX']*100,1),{s:round(label[d][2][s]*100,1) for s in LEAD}) for d in sorted(major)])

# Evaluate strictly chronological bearish warnings from completed SIP 5m bars.
# Separate no-future previous EVENING vs same day PREMARKET. A 5min candle starting t only known after t+5min.
# Definition is any two leaders negative since previous regular CLOSE and SOXX negative, with momentum vs 15min earlier.
# Search earliest signal before 9:20 ET, no follow-through assumptions.
all_signals={}
for i,d in enumerate(calendar):
 if i==0:continue
 prior=calendar[i-1]
 tps={s:stream(s,d) for s in S}
 times=sorted(set.intersection(*(set(tps[s]) for s in S)))
 previous={s:daily_map[s][prior][4] for s in S}
 for name,level,mom,required in [
     ('early_broad',.003,.002,2),
     ('confirmed_broad',.0075,.003,2),
     ('strict_3',.0075,.003,3),
     ('severe',.015,.007,2),
 ]:
  first=None
  for t in times:
   et=t.astimezone(E)
   if et.date().isoformat()==d:
    if not (4<=et.hour<9 or et.hour==9 and et.minute<=15):continue
   elif not (16<=et.hour<20):continue
   b={s:tps[s].get(t) for s in S};past={s:tps[s].get(t-T(minutes=15)) for s in S}
   if any(b[s] is None or past[s] is None for s in S):continue
   negative=sum((b[s][3]/previous[s]-1<=-level) and (b[s][3]/past[s][3]-1<=-mom) for s in LEAD)>=required
   etf=b['SOXX'][3]/previous['SOXX']-1<=-level/2 and b['SOXX'][3]/past['SOXX'][3]-1<=0
   if negative and etf:first=t+T(minutes=5);break
  all_signals[(d,name)]=first
for name in ('early_broad','confirmed_broad','strict_3','severe'):
 flagged={d for d in label if all_signals.get((d,name))}
 majors=flagged&major
 false=flagged-major
 print('RULE',name,'SIGNALS',len(flagged),'HITS_MAJOR',len(majors),'RECALL',round(len(majors)/len(major)*100,1),'FALSE_ALARMS_NONMAJOR',len(false),'PRECISION',round(len(majors)/len(flagged)*100,1) if flagged else 0,'BULLISH_DAYS_FLAGGED',sum(label[d][0]=='up' for d in flagged))
 times=collections.Counter('evening' if all_signals[(d,name)].date().isoformat()!=d else 'premarket' for d in majors)
 print('MAJOR_HIT_TIME_BUCKET',dict(times))
 print('MAJOR_MISSED',sorted(major-flagged))
 print('MAJOR_EARLIEST_TIMES',[(d,all_signals[(d,name)].astimezone(E).strftime('%m-%d %H:%M ET')) for d in sorted(majors)])
# Is prior downtrend of five completed trading days a major-down risk indicator?
for threshold in (.02,.04,.06):
 flagged=set()
 for i,day in enumerate(calendar):
  if i<6:continue
  old=calendar[i-6];pr=calendar[i-1]
  losses={s:daily_map[s][pr][4]/daily_map[s][old][4]-1 for s in S}
  if losses['SOXX']<=-threshold and sum(losses[s]<0 for s in LEAD)>=2:flagged.add(day)
 print('PRIOR5_BELOW',threshold,'FLAGGED_DAYS',len(flagged),'MAJOR_DAYS',len(flagged&major),'RISK_RATE',round(100*len(flagged&major)/len(flagged),1) if flagged else None)
