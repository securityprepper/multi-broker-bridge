"""Independent held-out analyses: midday opportunities and prior-five regimes."""
import json
from collections import defaultdict
from datetime import datetime, time, timedelta, date
from pathlib import Path
from statistics import mean
from research.v2_stock_risk_dayphase import ET,T5,T15,ingest
from research.v2_two_sided_daily_outcomes import (
    audited_days,sector_audit,signal,score_profit,EARLY_CUTOFF
)


def after_1030(bars, day, base, side="up", threshold=(.025,.010)):
    d=date.fromisoformat(day)
    for start in sorted(bars):
        if start.date() != d or not time(10,30) <= start.time() <= time(12,55):
            continue
        prev=bars.get(start-T15)
        if prev is None:
            continue
        row=bars[start]
        if signal(side,base,prev[3],row[3],*threshold):
            t=start+T5
            nextbar=bars.get(t)
            return dict(asof=t.isoformat(),signal_pct=round(100*(row[3]/base-1),3),
                        next_open=nextbar[0] if nextbar else None)
    return None


def symbol_prior5(symbols, calendar):
    by_symbol={}
    dates=[date.fromisoformat(x) for x in calendar]
    for sym,bars in symbols.items():
        close={dt.date():row[3] for dt,row in bars.items() if dt.time()==time(15,55)}
        out={}
        for i in range(6,len(dates)):
            history=dates[i-6:i] # SIX historical closes, five completed returns
            if any(d not in close for d in history):
                continue
            positive=sum(close[history[k+1]] > close[history[k]] for k in range(5))
            out[dates[i].isoformat()]=positive
        by_symbol[sym]=out
    return by_symbol


def stats(records, field, side="up"):
    x=[r for r in records if r[field]]
    outcome="major_up" if side=="up" else "major_down"
    scored=[r[field]["pnl_to14_pct"] for r in x if r[field].get("pnl_to14_pct") is not None]
    return dict(n_days=len(records), alerts=len(x), major_hit=sum(r[outcome] for r in x),
                avg14_pct=round(mean(scored),4) if scored else None,
                positive_trades=sum(v>0 for v in scored),
                negative_trades=sum(v<0 for v in scored))


def run():
    data=json.loads(Path('/tmp/semis_52weeks_alpaca_daily.json').read_text())['split']
    symbols=ingest(['/tmp/semis_52wk_5min_sip_adjusted.json',
                    '/tmp/semis_peers_52wk_5min_adjusted.json'])
    records,calendar=audited_days(symbols,data)
    sectors=sector_audit(symbols,calendar,data)
    prior=symbol_prior5(symbols,calendar)
    day_bars={}
    for sym,bars in symbols.items():
        d=defaultdict(dict)
        for t,row in bars.items():
            d[t.date().isoformat()][t]=row
        day_bars[sym]=d
    for r in records:
        r["prior5_up"]=prior[r["sym"]].get(r["day"])
        if not r["up_25_10"]:
            evt=after_1030(day_bars[r["sym"]].get(r["day"],{}),r["day"],r["base"])
            if evt:
                evt['pnl_to14_pct']=(round(score_profit(evt['next_open'],r['exit14']),4)
                                      if evt['next_open'] and r['exit14'] else None)
            r['midday_bull']=evt
        else:
            r['midday_bull']=None
        if not r['down_25_10']:
            r['midday_bear']=after_1030(day_bars[r['sym']].get(r['day'],{}),
                                        r['day'],r['base'],side='down')
        else:
            r['midday_bear']=None
    missed_up=[r for r in records if r['major_up'] and not r['up_25_10']]
    missed_down=[r for r in records if r['major_down'] and not r['down_25_10']]
    sector_daily = {r["day"]:r for r in sectors}
    sector_prior={}
    for i in range(6,len(calendar)):
        h=[sector_daily.get(x) for x in calendar[i-5:i]]
        if all(x is not None for x in h):
            sector_prior[calendar[i]]=sum(x["label"]=="positive" for x in h)
    sector_strata={}
    for regime in ("3plus_prior_positive","0to2_prior_positive"):
        members=[r for r in sectors if (sector_prior.get(r["day"],-1)>=3 if regime.startswith("3plus") else
                 0 <= sector_prior.get(r["day"],-1) <= 2)]
        chosen=[r["signal"]["pnl_to14_pct"] for r in members if r['signal']
                and r["signal"]["pnl_to14_pct"] is not None]
        sector_strata[regime]=dict(n_days=len(members),alerts=len(chosen),
           avg_net_proxy_14=round(mean(chosen),4) if chosen else None,
           win_count=sum(v>0 for v in chosen),
           strong_up_captured=sum(r['strong_soxx_up'] and bool(r['signal']) for r in members))
    regimes={}
    for which,later in (('earlier',False),('later',True)):
        for regime in ('3plus_previous_up_days','0to2_previous_up_days'):
            rows=[r for r in records if r['later']==later and r['prior5_up'] is not None
                  and (r['prior5_up']>=3)==regime.startswith('3plus')]
            regimes[f"{which}_{regime}"]=stats(rows,'up_25_10')
    mid_sig=[r for r in records if r['midday_bull']]
    mid_good=[r for r in mid_sig if r['midday_bull']['pnl_to14_pct'] is not None]
    results=dict(missed_up_big_by_early= len(missed_up),
       missed_down_big_by_early=len(missed_down),
       midday_additional_major_up=sum(r['major_up'] and r['midday_bull'] is not None for r in missed_up),
       midday_additional_major_down=sum(r['major_down'] and r['midday_bear'] is not None for r in missed_down),
       midday_up_alerts=len(mid_sig),
       midday_up_false_for_major_close=sum(not r['major_up'] for r in mid_sig),
       midday_up_scored=len(mid_good),
       midday_up_avg_net14=round(mean(r['midday_bull']['pnl_to14_pct'] for r in mid_good),4)
             if mid_good else None,
       midday_up_later_avg=round(mean(r['midday_bull']['pnl_to14_pct'] for r in mid_good if r['later']),4)
             if any(r['later'] for r in mid_good) else None,
       midday_up_win_count=sum(r['midday_bull']['pnl_to14_pct']>0 for r in mid_good),
       midday_missed_up_examples=[
         dict(day=r['day'],sym=r['sym'],close_pct=r['change_pct'],
              midday_alert=r['midday_bull']['asof'] if r['midday_bull'] else None)
         for r in sorted(missed_up,key=lambda x:-x['change_pct'])[:12]],
       individual_regime=regimes,sector_regime=sector_strata)
    print(json.dumps(results,indent=2,sort_keys=True))


if __name__=="__main__":
    run()
