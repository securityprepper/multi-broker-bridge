"""Independent READ-ONLY integrity verification of prospective V2 sector forecasts.

This verifier never issues signals, fetches prices, handles credentials, submits orders,
or revises source forecasts. It proves source journal/file/score agreement only.
Call after the first genuinely prospective policy session (>=2026-11-12).
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

ET=ZoneInfo("America/New_York")
SLOTS=("09:35","09:45","10:05")
SECTORS=("semiconductors","gold_miners","energy","financials","industrials","healthcare","software")
ARMS=("benchmark_side","peer_confirmed_side")
HORIZONS=("60m","flat")
SHA=re.compile(r"[a-f0-9]{64}\Z")
POLICY="v2-7sector-forward-baselines-20261111-r2"
POLICY_SHA256="629a5f7dab20d8ba4d5ed1e51b3947f658d4bb4971ffdf5e95ece2078fdf3ff3"
EFFECTIVE="2026-11-12"

class AuditError(ValueError):
    pass

def fail(reason):
    raise AuditError(reason)

def moment(x):
    try:
        d=datetime.fromisoformat(str(x).replace("Z","+00:00"))
        if d.tzinfo is None: fail("timestamp lacks timezone")
        return d.astimezone(ET)
    except (ValueError, TypeError, OverflowError) as e:
        raise AuditError("invalid timestamp") from e

def day_time(day, hm):
    return datetime.fromisoformat(day+"T"+hm).replace(tzinfo=ET)

def first_completed_bar_at_or_after(t):
    """Prevents using a five-minute closing bar before an issued+60m horizon."""
    local=moment(t.isoformat())
    midnight=local.replace(hour=0,minute=0,second=0,microsecond=0)
    seconds=(local-midnight).total_seconds()
    end=math.ceil(seconds/300)*300
    return midnight+timedelta(seconds=end)

def _seal(root, day, slot):
    if not root.is_absolute() or root.is_symlink():
        fail("unsafe state root")
    folder=root/day
    f=folder/(slot.replace(":","")+".json")
    if folder.is_symlink() or f.is_symlink() or not f.is_file():
        fail("missing/unsafe original forecast seal: "+slot)
    raw=f.read_bytes()
    digest=sha256(raw).hexdigest()
    doc=json.loads(raw)
    if doc.get("schema_version") != 2 or doc.get("research_only") is not True:
        fail("old or non-research original forecast")
    if doc.get("forecast_slot_ET")!=slot or doc.get("forecast_policy_id")!=POLICY:
        fail("inconsistent slot or policy identifier")
    policy_sha=doc.get("forecast_policy_sha256")
    if not isinstance(policy_sha,str) or policy_sha!=POLICY_SHA256:
        fail("incorrect frozen policy digest")
    if not (doc.get("PAPER_orders_allowed") is False and
            doc.get("LIVE_orders_allowed") is False and
            doc.get("orders_submitted")==0 and
            doc.get("no_current_or_future_outcomes_in_document") is True):
        fail("unexpected source permission or future-outcome field")
    observed=moment(doc["time_of_observation_ET"])
    issued=moment(doc["forecast_actual_issued_at_ET"])
    if (observed.date().isoformat()!=day or issued.date().isoformat()!=day
            or observed>issued or issued<day_time(day,slot)
            or issued>day_time(day,slot)+timedelta(seconds=90)):
        fail("unverifiable forecast issuance chronology")
    if set(doc.get("sectors",{}))!=set(SECTORS):
        fail("original forecast not complete for seven sectors")
    for sector in SECTORS:
        row=doc["sectors"][sector]
        forecast=row.get("forward_forecast")
        if not isinstance(forecast,dict):
            fail("missing original sector policy decision")
        if (forecast.get("policy_sha256")!=policy_sha or
            forecast.get("policy_id")!=POLICY or
            moment(forecast.get("signal_recorded_at_ET"))!=issued):
            fail("sector policy or issuance mismatch")
        for arm,display in (("benchmark_side","shadow_classification"),
                            ("peer_confirmed_side","peer_confirmed_classification")):
            if forecast.get(arm) not in ("UP","DOWN","ABSTAIN") or row.get(display)!=forecast[arm]:
                fail("original directional decision mismatch")
        if not (forecast.get("orders_authorized") is False and
                forecast.get("alerts_authorized") is False):
            fail("unapproved alert/order interface")
        mark=forecast.get("signal_mark")
        if mark is None:
            if any(forecast[a]!="ABSTAIN" for a in ARMS):
                fail("issued side without as-of mark")
        else:
            if not isinstance(mark,(float,int)) or not math.isfinite(mark) or mark<=0:
                fail("invalid original as-of price")
            if moment(forecast["signal_source_bar_end_ET"])>observed:
                fail("source bar from future")
    return doc,raw,digest,issued

def issuance_journal(journal, day, slot, digest, issued):
    matched=[]
    for item in journal:
        if not isinstance(item,dict):continue
        try: msg=json.loads(item.get("MESSAGE",""))
        except (TypeError,ValueError):continue
        if not isinstance(msg,dict):continue
        if (msg.get("status")!="RESEARCH_SHADOW_SEALED" or
            msg.get("day")!=day or msg.get("slot")!=slot):
            continue
        if msg.get("orders_submitted")!=0:
            fail("journal reported broker orders")
        sh=msg.get("sealed_file_sha256")
        if not isinstance(sh,str) or not SHA.fullmatch(sh):
            fail("missing recorded issuance hash")
        if sh!=digest:fail("issued journal hash differs from sealed file")
        try:
            stamp=datetime.fromtimestamp(int(item["__REALTIME_TIMESTAMP"])/1_000_000,
                                        timezone.utc).astimezone(ET)
        except (KeyError,TypeError,ValueError,OverflowError):
            fail("journal has no trusted realtime timestamp")
        if (stamp.date().isoformat()!=day or
            stamp<issued-timedelta(seconds=15) or
            stamp>issued+timedelta(seconds=120) or
            stamp>=day_time(day,slot)+timedelta(hours=1)):
            fail("journal seal is after future outcome or inconsistent with signal")
        matched.append(stamp)
    if len(matched)!=1:
        fail("missing or duplicate initial seal receipt: "+slot)
    return matched[0]

def _check_score(root,day,seals):
    f=root/"scores"/day/"1340CT.json"
    if f.is_symlink() or not f.is_file():
        fail("missing sealed independent outcome score")
    score=json.loads(f.read_bytes())
    if (score.get("schema_version")!=1 or score.get("research_only") is not True or
        score.get("orders_submitted")!=0 or
        score.get("PAPER_orders_allowed") is not False or
        score.get("LIVE_orders_allowed") is not False or
        score.get("capture_complete") is not True or
        score.get("forecast_policy_id")!=POLICY or
        score.get("forecast_policy_sha256")!=seals[SLOTS[0]][0]["forecast_policy_sha256"] or
        score.get("sealed_slots")!=sorted(SLOTS)):
        fail("outcome score schema/policy/coverage mismatch")
    if moment(score["scored_at_ET"])<day_time(day,"14:50"):
        fail("outcome score completed too early")
    data=score.get("scores")
    if not isinstance(data,list) or len(data)!=len(SLOTS)*len(SECTORS)*len(ARMS)*len(HORIZONS):
        fail("missing or duplicated outcome entries")
    expected_keys={(s,t,a,h) for s in SLOTS for t in SECTORS for a in ARMS for h in HORIZONS}
    actual_keys=set()
    for row in data:
        if not isinstance(row,dict):fail("invalid score row")
        slot=row.get("slot_ET")
        sector=row.get("sector")
        arm=row.get("arm")
        horizon=row.get("horizon")
        key=(slot,sector,arm,horizon)
        if key not in expected_keys or key in actual_keys:
            fail("unknown or duplicate forecast score")
        actual_keys.add(key)
        original,_,digest,issued=seals[slot]
        prior=original["sectors"][sector]["forward_forecast"]
        if (row.get("source_document_sha256")!=digest or
            row.get("policy_id")!=POLICY or
            row.get("policy_sha256")!=original["forecast_policy_sha256"] or
            row.get("forecast")!=prior[arm] or
            row.get("signal_mark")!=prior.get("signal_mark") or
            moment(row["signal_issued_at_ET"])!=issued or
            row.get("signal_bar_end_ET")!=prior.get("signal_source_bar_end_ET")):
            fail("score does not match original issued forecast")
        horizon_end=(first_completed_bar_at_or_after(issued+timedelta(minutes=60))
                     if horizon=="60m" else day_time(day,"14:40"))
        if moment(row["future_at_ET"])!=horizon_end or horizon_end<=issued:
            fail("outcome horizon not strictly after original signal")
        side=prior[arm]
        signed=row.get("signed_return_pct")
        net30=row.get("modeled_after_30bp_pct")
        net60=row.get("modeled_after_60bp_pct")
        future=row.get("future_mark")
        if side=="ABSTAIN":
            if signed is not None or net30 is not None or net60 is not None or row.get("direction")!="ABSTAIN":
                fail("abstention was credited as a trade or predictive hit")
        elif future is None:
            if signed is not None or net30 is not None or net60 is not None or row.get("direction")!="MISSING_OUTCOME":
                fail("missing outcome was credited as prediction")
        else:
            if not isinstance(future,(int,float)) or not math.isfinite(future) or future<=0:
                fail("invalid future mark")
            mark=prior.get("signal_mark")
            if mark is None:fail("directional score has no original mark")
            ret=100*(future/mark-1)
            expected=ret*(1 if side=="UP" else -1)
            if abs(float(signed)-expected)>0.00001:
                fail("signed outcome includes prior price movement or wrong side")
            label=("TINY_NOT_A_HIT" if abs(ret)<0.05 else
                   "HIT" if expected>0 else "MISS")
            if row.get("direction")!=label:
                fail("flat/tiny move incorrectly credited as a hit")
            if (abs(float(net30)-(expected-.30))>0.00001 or
                abs(float(net60)-(expected-.60))>0.00001):
                fail("friction adjustment arithmetic mismatch")
    if actual_keys!=expected_keys:fail("outcome combinations incomplete")
    return {"status":"PASS_SOURCE_AND_SCORE_AGREE","day_ET":day,
            "sealed_slots":len(SLOTS),"sectors":len(SECTORS),
            "forecast_outcome_rows_verified":len(data),
            "broker_orders":0}

def verify(root,day,journal,require_score=True):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",day) or day<EFFECTIVE:
        fail("outside precommitted prospective policy start")
    seals={}
    journals={}
    for slot in SLOTS:
        seals[slot]=_seal(root,day,slot)
        journals[slot]=issuance_journal(journal,day,slot,seals[slot][2],seals[slot][3])
    if not require_score:
        return {"status":"PASS_ISSUANCE_ONLY_OUTCOMES_PENDING","day_ET":day,
                "sealed_slots":len(seals),"sectors":len(SECTORS),"broker_orders":0}
    return _check_score(root,day,seals)

def main(argv=None):
    p=argparse.ArgumentParser(description="Offline V2 journal+file+future-only score verifier")
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--day",required=True)
    p.add_argument("--journal-jsonl",required=True,type=Path)
    p.add_argument("--issuance-only",action="store_true")
    args=p.parse_args(argv)
    try:
        with args.journal_jsonl.open() as f:
            journal=[json.loads(s) for s in f if s.strip()]
        out=verify(args.root,args.day,journal,not args.issuance_only)
        print(json.dumps(out,sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError,IndexError,ZeroDivisionError) as e:
        print(json.dumps({"status":"RESEARCH_INTEGRITY_UNVERIFIED",
                          "reason":type(e).__name__,
                          "orders_submitted":0}),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
