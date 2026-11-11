"""Research-only SEC Item 1.05 event provenance and frozen-shadow coverage audit.
No live polling, broker/account/order calls, alerting, or trading permissions.
Historical SEC accepted_at is publication metadata, NOT collector first_seen.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from typing import Mapping
import json
import re

ACCESSION = re.compile(r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
CIK = re.compile(r"^[0-9]{1,10}$")
REQUIRED_KEYS = ("form","items","accession","issuer_cik","acceptance_at")

def utc(text: str)->datetime:
    if not isinstance(text,str):raise ValueError("timestamp must be a string")
    value=datetime.fromisoformat(text.replace("Z","+00:00"))
    if value.tzinfo is None:raise ValueError("naive timestamp")
    return value.astimezone(timezone.utc)

def split_items(raw)->set[str]:
    if not isinstance(raw,str):raise ValueError("no trusted SEC items")
    items={s.strip() for s in re.split(r"[,;]",raw) if s.strip()}
    if not items or any(not re.fullmatch(r"\d+\.\d+",i) for i in items):
        raise ValueError("invalid SEC item list")
    return items

def normalized_cik(value):
    if value is None or not CIK.fullmatch(str(value)):raise ValueError("invalid CIK")
    return str(int(str(value))).zfill(10)

def source_status(row:Mapping,asof:str,verified_issuer_cik:str):
    """Pure research classification: always allowed_to_order=False."""
    result={"research_only":True,"allowed_to_order":False,
            "allowed_to_notify":False,"status":"UNVERIFIED"}
    try:
        for k in REQUIRED_KEYS:
            if k not in row:raise ValueError("missing required field")
        if row["form"] not in ("8-K","8-K/A"):
            result["status"]="NOT_8K";return result
        if "1.05" not in split_items(row["items"]):
            result["status"]="NOT_ITEM_105";return result
        if row["form"]=="8-K/A":
            result["status"]="AMENDMENT_NOT_NEW_ORIGINAL_EVENT";return result
        if not ACCESSION.fullmatch(str(row["accession"])):
            raise ValueError("invalid accession")
        if normalized_cik(row["issuer_cik"])!=normalized_cik(verified_issuer_cik):
            result["status"]="ISSUER_CIK_MISMATCH";return result
        accepted=utc(row["acceptance_at"]);decision=utc(asof)
        if accepted>decision:
            result["status"]="FUTURE_ACCEPTANCE";return result
        first=row.get("first_observed_at")
        if first is None:
            result["status"]="NO_ORIGINAL_FIRST_OBSERVED";return result
        first=utc(first)
        if first<accepted:
            result["status"]="FIRST_OBSERVED_BEFORE_SEC_ACCEPTED";return result
        if first>decision:
            result["status"]="FUTURE_FIRST_OBSERVED";return result
        digest=row.get("first_observed_content_sha256")
        if not isinstance(digest,str) or not SHA.fullmatch(digest):
            result["status"]="NO_IMMUTABLE_ORIGINAL_CONTENT_DIGEST";return result
        original=row.get("original_content")
        if original is None or not isinstance(original,str):
            result["status"]="NO_FIRST_VERSION_TEXT";return result
        if sha256(original.encode("utf-8")).hexdigest()!=digest:
            result["status"]="VERSION_HASH_MISMATCH";return result
        # Filing acceptance is often days after an incident; no tradable
        # predictive edge may be deduced without independent news and quotes.
        result["status"]="SOURCE_SNAPSHOT_VERIFIED_RESEARCH_ONLY"
        return result
    except (KeyError,TypeError,ValueError,OverflowError):
        result["status"]="INVALID_OR_UNTRUSTED_SOURCE"
        return result

def extract_recent(recent:Mapping,cik:int|str)->list[dict]:
    """SEC submissions 'recent' parallel arrays, never scan document text for items."""
    required=("form","items","accessionNumber","acceptanceDateTime")
    if any(not isinstance(recent.get(k),list) for k in required):
        raise ValueError("missing SEC recent parallel arrays")
    n=len(recent["form"])
    if any(len(recent[k])!=n for k in required):
        raise ValueError("incomplete SEC recent parallel arrays")
    result=[]
    for i in range(n):
        form=recent["form"][i]
        if form not in ("8-K","8-K/A"):continue
        try:items=split_items(recent["items"][i])
        except ValueError:continue
        if "1.05" not in items:continue
        row={"form":form,"items":recent["items"][i],
             "accession":recent["accessionNumber"][i],
             "acceptance_at":recent["acceptanceDateTime"][i],
             "issuer_cik":normalized_cik(cik)}
        result.append(row)
    return result

def sealed_progress(root:Path, dates:tuple[str,...])->dict:
    """Read-only counts. A feature snapshot is not an issued forecast."""
    captures=complete=forecasts=missing=0
    per_day={}
    for day in dates:
        details={"snapshots":0,"feature_sectors":0,"emitted_forecasts":0,
                 "abstained_sectors":0,"missing_files":0}
        for slot in ("0935","0945","1005"):
            p=root/day/f"{slot}.json"
            if not p.is_file():
                details["missing_files"]+=1;missing+=1;continue
            x=json.loads(p.read_text())
            if not (x.get("research_only") is True and
                    x.get("orders_submitted")==0 and
                    x.get("no_current_or_future_outcomes_in_document") is True):
                raise ValueError("untrusted shadow source")
            if x.get("forecast_slot_ET")!=slot[:2]+":"+slot[2:]:
                raise ValueError("slot mismatch")
            captures+=1;details["snapshots"]+=1
            if not isinstance(x.get("sectors"),dict):
                raise ValueError("sector map missing")
            for v in x["sectors"].values():
                if v.get("status")=="ASOF_FEATURES":
                    complete+=1;details["feature_sectors"]+=1
                if v.get("status")=="ABSTAIN_MISSING_ASOF_DATA":
                    details["abstained_sectors"]+=1
                if v.get("shadow_classification") is not None:
                    forecasts+=1;details["emitted_forecasts"]+=1
        per_day[day]=details
    return {"snapshots":captures,"asof_feature_sector_slots":complete,
            "actual_precommitted_forecast_sector_slots":forecasts,
            "missing_slots":missing,"days":per_day,
            "research_only":True,"allowed_to_order":False}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--shadow-root",type=Path,required=True)
    p.add_argument("--days",nargs="+",required=True)
    a=p.parse_args()
    print(json.dumps(sealed_progress(a.shadow_root,tuple(a.days)),indent=2,sort_keys=True))