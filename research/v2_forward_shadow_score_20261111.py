"""GET-only, separately sealed outcomes for *previously issued* seven-sector forecasts.
Never computes a new forecast. Never modifies raw sealed before-outcome snapshots.
Only evaluate after 14:40 ET + 10m availability buffer, using 5Min SIP trade marks.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import v2_forward_only_sector_shadow_20261109 as capture
from .v2_sector_forecast_policy_20261111 import POLICY, POLICY_ID, POLICY_SHA256

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
ARMS = ("benchmark_side", "peer_confirmed_side")
HORIZONS = ("60m", "flat")
DIRECTIONS = {"UP", "DOWN", "ABSTAIN"}
MIN_SCORE_TIME = (14, 50)
TARGET_FLAT = (14, 40)

def _parse(s):
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("timestamp timezone required")
    return d.astimezone(ET)

def _time_at(day, hhmm):
    return datetime.fromisoformat(day + "T" + hhmm).replace(tzinfo=ET)

def validate_seal(content, day, slot):
    """Reject earlier schema-v1 archives, altered provenance or future-informed files."""
    source = json.loads(content)
    if not isinstance(source, dict) or source.get("schema_version") != 2:
        raise ValueError("not a prospective schema-2 issued forecast")
    if (source.get("research_only") is not True or source.get("PAPER_orders_allowed") is not False
        or source.get("LIVE_orders_allowed") is not False or source.get("orders_submitted") != 0
        or source.get("no_current_or_future_outcomes_in_document") is not True):
        raise ValueError("unsupported source permissions or non-forecast document")
    if (source.get("forecast_slot_ET") != slot
        or source.get("forecast_policy_id") != POLICY_ID
        or source.get("forecast_policy_sha256") != POLICY_SHA256):
        raise ValueError("mismatched forecast slot or frozen policy hash")
    start = _parse(source["time_of_observation_ET"])
    issued = _parse(source["forecast_actual_issued_at_ET"])
    if not (start.date().isoformat() == day and issued.date().isoformat() == day
            and start <= issued and capture.slot(issued) == slot):
        raise ValueError("invalid actual issuance chronology")
    if set(source.get("sectors", {})) != set(capture.SECTORS):
        raise ValueError("partial sector forecast coverage")
    for sector, (etf, _) in capture.SECTORS.items():
        row = source["sectors"][sector]
        f = row.get("forward_forecast")
        if not isinstance(f, dict):
            raise ValueError("sector missing original forecast")
        if (f.get("policy_id") != POLICY_ID or f.get("policy_sha256") != POLICY_SHA256
            or f.get("sector") != sector or f.get("etf") != etf
            or f.get("signal_recorded_at_ET") != issued.isoformat()):
            raise ValueError("sector forecast provenance mismatch")
        if (f.get("benchmark_side") not in DIRECTIONS
            or f.get("peer_confirmed_side") not in DIRECTIONS
            or row.get("shadow_classification") != f["benchmark_side"]
            or row.get("peer_confirmed_classification") != f["peer_confirmed_side"]
            or f.get("orders_authorized") is not False
            or f.get("alerts_authorized") is not False):
            raise ValueError("unverified forecast side/permission")
        mark=f.get("signal_mark")
        if mark is not None:
            if not isinstance(mark,(int,float)) or not math.isfinite(mark) or mark <= 0:
                raise ValueError("invalid source signal mark")
            bar_end=_parse(f["signal_source_bar_end_ET"])
            if not (bar_end <= start <= issued):
                raise ValueError("post-issuance or unfinished signal bar")
            raw_mark=row.get("features",{}).get(etf,{}).get("observed_price")
            if raw_mark != mark:
                raise ValueError("signal source price changed")
        elif any(f[arm]!="ABSTAIN" for arm in ARMS):
            raise ValueError("directional forecast missing mark")
    return source

def outcome_bar(live, symbol, local_end):
    """Exactly the precommitted completed bar ending at the evaluation time."""
    if local_end.tzinfo is None:
        raise ValueError("outcome end timezone required")
    beginning=local_end.astimezone(ET)-timedelta(minutes=5)
    bar=live.get(symbol,{}).get(beginning.strftime("%Y-%m-%d %H:%M"))
    if not isinstance(bar,dict):
        return None
    observed_end=_parse(bar["bar_available_after_ET"])
    if observed_end!=local_end.astimezone(ET):
        raise ValueError("wrong outcome bar or time")
    close=float(bar["close"])
    if not math.isfinite(close) or close<=0:
        raise ValueError("invalid outcome mark")
    return close

def score_one(side, initial, future):
    """Tiny and flat returns are never credited as successful forecasts."""
    if side == "ABSTAIN":
        return {"direction":"ABSTAIN","signed_return_pct":None,"modeled_after_30bp_pct":None,
                "modeled_after_60bp_pct":None}
    if future is None or initial is None:
        return {"direction":"MISSING_OUTCOME","signed_return_pct":None,"modeled_after_30bp_pct":None,
                "modeled_after_60bp_pct":None}
    change=100*(future/initial-1)
    signed=change*(1 if side=="UP" else -1)
    if abs(change)<POLICY["outcome"]["tiny_return_below_absolute_pct"]:
        label="TINY_NOT_A_HIT"
    elif signed>0:
        label="HIT"
    else:
        label="MISS"
    return {"direction":label,"signed_return_pct":round(signed,6),
            "modeled_after_30bp_pct":round(signed-0.30,6),
            "modeled_after_60bp_pct":round(signed-0.60,6)}

def evaluate_seals(day, source_seals, market_bars):
    rows = []
    for slot in capture.SLOTS:
        item=source_seals.get(slot)
        if item is None:
            rows.append({"slot_ET":slot,"sector":None,"status":"MISSING_FORECAST_SEAL"})
            continue
        source, digest=item
        issued = _parse(source["forecast_actual_issued_at_ET"])
        evaluation={"60m":_time_at(day,slot)+timedelta(minutes=60),
                    "flat":_time_at(day,"14:40")}
        for sector, (etf, _) in capture.SECTORS.items():
            f=source["sectors"][sector]["forward_forecast"]
            price=f.get("signal_mark")
            for horizon,end in evaluation.items():
                if end<=issued:
                    raise ValueError("outcome evaluation not after issuance")
                future=outcome_bar(market_bars,etf,end)
                for arm in ARMS:
                    side=f[arm]
                    score=score_one(side,price,future)
                    rows.append({"slot_ET":slot,"sector":sector,"etf":etf,
                                 "arm":arm,"forecast":side,"policy_id":POLICY_ID,
                                 "policy_sha256":POLICY_SHA256,
                                 "signal_issued_at_ET":issued.isoformat(),
                                 "signal_bar_end_ET":f.get("signal_source_bar_end_ET"),
                                 "source_document_sha256":digest,
                                 "signal_mark":price,"horizon":horizon,
                                 "future_at_ET":end.isoformat(),"future_mark":future,
                                 **score})
    summary={}
    for sector in capture.SECTORS:
        summary[sector]={}
        for arm in ARMS:
            summary[sector][arm]={}
            for horizon in HORIZONS:
                subset=[x for x in rows if x.get("sector")==sector and x.get("arm")==arm and x.get("horizon")==horizon]
                summary[sector][arm][horizon]={
                    "issued":sum(x.get("forecast") in ("UP","DOWN") for x in subset),
                    "abstentions":sum(x.get("forecast")=="ABSTAIN" for x in subset),
                    "hits":sum(x.get("direction")=="HIT" for x in subset),
                    "misses":sum(x.get("direction")=="MISS" for x in subset),
                    "tiny":sum(x.get("direction")=="TINY_NOT_A_HIT" for x in subset),
                    "missing_outcome":sum(x.get("direction")=="MISSING_OUTCOME" for x in subset),
                    "modeled_winners_30bp":sum(x.get("modeled_after_30bp_pct") is not None and x["modeled_after_30bp_pct"]>0 for x in subset),
                }
    return rows,summary

def _atomic_new(path,doc):
    path.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
    if path.parent.is_symlink():
        raise ValueError("symlink score directory")
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,"w") as file:
            json.dump(doc,file,sort_keys=True)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise

def run(now=None, holiday_check=capture.holiday_unpaused, fetch=capture.fetch_bars):
    now=now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("score clock must have timezone")
    local=now.astimezone(ET)
    if local.weekday()>=5 or (local.hour,local.minute)<MIN_SCORE_TIME:
        return {"status":"NOT_SCORE_TIME","market_data_requests":0,"orders_submitted":0}
    if not holiday_check(now):
        return {"status":"HOLIDAY_PAUSED_NO_SCORE_OR_POLL","market_data_requests":0,"orders_submitted":0}
    state=Path(os.environ.get("V2_SHADOW_STATE_ROOT",""))
    if not state.is_absolute() or not state.is_dir() or state.is_symlink():
        raise ValueError("unsafe scoreboard state root")
    day=local.date().isoformat()
    output=state/"scores"/day/"1340CT.json"
    if output.exists():
        return {"status":"SCORES_ALREADY_SEALED","market_data_requests":0,"orders_submitted":0}
    seals={}
    for slot in capture.SLOTS:
        path=state/day/(slot.replace(":","")+".json")
        if not path.is_file() or path.is_symlink():
            continue
        raw=path.read_bytes()
        seals[slot]=(validate_seal(raw,day,slot),hashlib.sha256(raw).hexdigest())
    if not seals:
        return {"status":"NO_NEW_SCHEMA_FORECAST_SEALS","market_data_requests":0,"orders_submitted":0}
    creds=Path(os.environ.get("CREDENTIALS_DIRECTORY",""))
    bars=capture.validate_live_bars(fetch(now,"5Min",creds),now)
    rows,summary=evaluate_seals(day,seals,bars)
    doc={"schema_version":1,"day_ET":day,"scored_at_ET":local.isoformat(),
         "research_only":True,"orders_submitted":0,"PAPER_orders_allowed":False,
         "LIVE_orders_allowed":False,"alerts_allowed":False,
         "forecast_policy_id":POLICY_ID,"forecast_policy_sha256":POLICY_SHA256,
         "capture_complete":len(seals)==len(capture.SLOTS),
         "sealed_slots":sorted(seals),
         "missing_slots":[s for s in capture.SLOTS if s not in seals],
         "outcome_source":"Alpaca SIP completed 5Min trade bars GET-only; marks, not NBBO fills",
         "future_bar_lookahead_in_forecasts":False,
         "illustrative_friction_only":True,
         "signals_and_outcomes_are_separate_immutable_files":True,
         "scores":rows,"summary":summary}
    _atomic_new(output,doc)
    return {"status":"RESEARCH_OUTCOMES_SEALED","day":day,
            "slots":len(seals),"forecast_rows":len(rows),
            "orders_submitted":0,"market_data_requests":1}

if __name__=="__main__":
    try:
        print(json.dumps(run(),sort_keys=True))
    except FileExistsError:
        print(json.dumps({"status":"SCORES_ALREADY_SEALED","orders_submitted":0}))
    except (OSError,TypeError,ValueError,KeyError,TimeoutError,json.JSONDecodeError) as exc:
        print(json.dumps({"status":"RESEARCH_SCORE_FAILED_CLOSED","kind":type(exc).__name__,
                          "orders_submitted":0}))
        raise SystemExit(2)
