"""Root-owned issuer/SEC/licensed-news attestation publisher for Alpaca PAPER BUY clearance.

Only independently attested, complete, original-evidence source bundles can yield
NEWS_CLEAR_ASOF; screens only Chicago YESTERDAY and TODAY, not thirty-day news
coverage. No broker / market-data GET / HTTP / Pushover / LIVE permissions.
Absence/ambiguity => NO FILE and NEWS_UNKNOWN in every receiving broker.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,stat,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone,date
from zoneinfo import ZoneInfo
from recommendation_paper_bridge.news_eligibility import (
    evaluate_news_asof,CLEAR,yesterday_today_start
)

SOURCE=Path("/etc/securityprepper/recommendation-paper-bridge/news-source-proofs")
OUTPUT=Path("/etc/securityprepper/recommendation-paper-bridge/news-clearance")
STATUS=Path("/var/lib/securityprepper-news-clearance-publisher/status.json")
GATE=Path("/var/lib/securityprepper-v2-forward-shadow/holiday_gate.json")
NEWS_CACHE=Path("/var/lib/securityprepper-news-watch-v2/current.json")
SEC_CACHE=Path("/var/lib/securityprepper-earnings-watch-v1/sec-official-earnings.json")
EARNINGS_ATTEST=Path("/etc/securityprepper/earnings-attestations")
PRODUCER="trusted_issuer_sec_news_attestor_v1"
SYMBOL=re.compile(r"[A-Z][A-Z0-9.]{0,11}\Z")
MAX_BUNDLE=256*1024

class EvidenceBlocked(ValueError):pass

def when(raw):
    if not isinstance(raw,str):raise EvidenceBlocked("TIMESTAMP_MISSING")
    try:t=datetime.fromisoformat(raw.replace("Z","+00:00"))
    except (TypeError,ValueError) as exc:raise EvidenceBlocked("TIMESTAMP_INVALID") from exc
    if t.tzinfo is None:raise EvidenceBlocked("TIMESTAMP_NAIVE")
    return t.astimezone(timezone.utc)

def owner_protected(path,*,directory=False):
    if path.is_symlink():raise EvidenceBlocked("UNTRUSTED_SYMLINK")
    st=path.lstat()
    if st.st_uid!=0 or st.st_mode & 0o022:
        raise EvidenceBlocked("UNTRUSTED_OWNER_OR_MODE")
    if directory and not stat.S_ISDIR(st.st_mode):
        raise EvidenceBlocked("UNTRUSTED_DIRECTORY")
    if not directory and (not stat.S_ISREG(st.st_mode) or st.st_nlink!=1):
        raise EvidenceBlocked("UNTRUSTED_FILE")

def safe_read(path):
    owner_protected(path.parent,directory=True)
    owner_protected(path)
    fd=os.open(str(path),os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
    try:
        st=os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or
            st.st_mode&0o022 or st.st_nlink!=1 or
            st.st_size<=0 or st.st_size>MAX_BUNDLE):
            raise EvidenceBlocked("BUNDLE_SIZE_INVALID_OR_UNTRUSTED")
        blob=os.read(fd,MAX_BUNDLE+1)
        if len(blob)>MAX_BUNDLE:raise EvidenceBlocked("BUNDLE_OVERSIZE")
    finally:os.close(fd)
    return json.loads(blob)

def holiday_allows(doc,now):
    if not isinstance(doc,dict) or doc.get("timezone")!="America/Chicago" or doc.get("paused") is not False or doc.get("calendar_coverage_ok") is not True:
        return False
    try:
        expiry=when(doc["next_check_at"])
        coverage=date.fromisoformat(doc["calendar_coverage_through"])
        revision=int(doc["calendar_revision"])
    except (KeyError,ValueError,TypeError,EvidenceBlocked):return False
    return revision>=2 and now<expiry and coverage>=now.astimezone(ZoneInfo("America/Chicago")).date()

def eligible_bundle(symbol,doc,now):
    if (not isinstance(doc,dict) or doc.get("schema_version")!=1 or
        doc.get("source_scope")!="COMPLETE_INDEPENDENT_YESTERDAY_TODAY_ISSUER_SEC_LICENSED_NEWS"):
        raise EvidenceBlocked("UNPROVEN_COMPLETE_YESTERDAY_TODAY_SOURCE_SCOPE")
    window_start=yesterday_today_start(now)
    if (doc.get("window_timezone")!="America/Chicago" or
        when(doc.get("screening_start_utc"))!=window_start):
        raise EvidenceBlocked("SCREENING_WINDOW_NOT_YESTERDAY_TODAY")
    if (doc.get("symbol")!=symbol or
        doc.get("issuer_cik") is None or
        doc.get("exchange") not in {"NYSE","NASDAQ","AMEX"}):
        raise EvidenceBlocked("ISSUER_IDENTITY_NOT_VERIFIED")
    # This source manifest must have been freshly and independently collected
    # by a trusted root-owned upstream producer, not retroactively backfilled.
    fetched=when(doc.get("fresh_collector_observed_at_utc"))
    if not timedelta(0)<=now-fetched<=timedelta(seconds=60):
        raise EvidenceBlocked("SOURCE_COLLECTION_NOT_FRESH")
    sources=doc.get("independent_source_receipts")
    if not isinstance(sources,dict) or set(sources)!={"issuer_ir","sec_edgar","licensed_news"}:
        raise EvidenceBlocked("THREE_INDEPENDENT_SOURCE_RECEIPTS_MISSING")
    for name,details in sources.items():
        if (not isinstance(details,dict) or details.get("verified_original_snapshot") is not True
            or not details.get("provider_reference") or
            not re.fullmatch(r"[0-9a-f]{64}",str(details.get("original_receipt_sha256","")))
            or not timedelta(0)<=now-when(details.get("received_at_utc"))<=timedelta(seconds=120)
            or when(details.get("coverage_since_utc"))>window_start
            or not now-timedelta(seconds=60)<=when(details.get("coverage_through_utc"))<=now
            or details.get("full_pagination_or_feed_coverage_proven") is not True):
            raise EvidenceBlocked("SOURCE_ORIGINAL_RECEIPT_INCOMPLETE")
    try:
        outcome=evaluate_news_asof(
            symbol=symbol,exchange=doc["exchange"],issuer_cik=doc["issuer_cik"],
            asof_utc=now.isoformat(),identity=doc["identity"],
            coverage=doc["coverage"],evidence=doc["evidence"])
    except (ValueError,KeyError,TypeError) as exc:
        raise EvidenceBlocked("SOURCE_EVIDENCE_UNVERIFIED") from exc
    if outcome.get("status")!=CLEAR or outcome.get("paper_order_eligible") is not True:
        raise EvidenceBlocked("NOT_NEWS_CLEAR_ASOF_"+str(outcome.get("status","UNKNOWN")))
    return {"schema_version":1,"producer":PRODUCER,"symbol":symbol,
        "exchange":doc["exchange"],"issuer_cik":doc["issuer_cik"],
        "produced_at_utc":now.isoformat(),"identity":doc["identity"],
        "window_timezone":"America/Chicago",
        "adverse_news_screening_start_utc":window_start.isoformat(),
        "coverage":doc["coverage"],"evidence":doc["evidence"],
        "source_bundle_sha256":hashlib.sha256(json.dumps(doc,sort_keys=True,separators=(",",":")).encode()).hexdigest()}

def atomic_write(destination,doc):
    owner_protected(destination.parent,directory=True)
    if destination.is_symlink():raise EvidenceBlocked("DEST_SYMLINK")
    if destination.exists():owner_protected(destination)
    content=(json.dumps(doc,sort_keys=True,separators=(",",":"))+"\n").encode()
    if len(content)>MAX_BUNDLE:raise EvidenceBlocked("OUTPUT_OVERFLOW")
    fd,temp=tempfile.mkstemp(prefix=".news-proof-",dir=destination.parent)
    try:
        with os.fdopen(fd,"wb") as out:
            out.write(content);out.flush();os.fsync(out.fileno())
            os.fchmod(out.fileno(),0o640)
            os.fchown(out.fileno(),0,destination.parent.stat().st_gid)
        os.replace(temp,destination)
        if hashlib.sha256(destination.read_bytes()).digest()!=hashlib.sha256(content).digest():
            raise EvidenceBlocked("OUTPUT_READBACK_MISMATCH")
    finally:
        if os.path.exists(temp):os.unlink(temp)

def observed_coverage_gaps():
    # Observed coverage does NOT certify full Chicago yesterday+today review.
    out={"source_bundle_dir_exists":SOURCE.exists(),
        "source_bundle_count":len(list(SOURCE.glob("*.json"))) if SOURCE.is_dir() else 0,
        "adverse_news_review_window":"YESTERDAY_AND_TODAY_AMERICA_CHICAGO",
        "issuer_ir_yesterday_today_complete":"UNVERIFIED",
        "sec_all_material_filings_yesterday_today_complete":"UNVERIFIED",
        "licensed_news_yesterday_today_full_pagination":"UNVERIFIED"}
    try:
        x=json.loads(NEWS_CACHE.read_text())
        out.update({"news_cache_recent_window":len(x.get("recent",[])),
           "news_cache_receipt_time_basis":x.get("first_seen_time_basis") or "UNKNOWN"})
    except (OSError,ValueError,TypeError):out["news_cache_status"]="UNAVAILABLE"
    try:
        x=json.loads(SEC_CACHE.read_text())
        out["event_specific_SEC_earnings_proofs"]=len(x.get("proofs",{}))
    except (OSError,ValueError,TypeError):out["event_specific_SEC_earnings_proofs"]="UNKNOWN"
    try:
        out["event_specific_issuer_earnings_attestations"]=len(list(EARNINGS_ATTEST.glob("*.json")))
    except OSError:out["event_specific_issuer_earnings_attestations"]="UNKNOWN"
    return out

def revoke_unqualified_proof(output,symbol):
    """Immediately revoke a previously signed BUY clearance if a source fails.

    An orphan/stale clearance must not remain BUY-eligible for its remaining
    freshness interval after the collector loses coverage or finds adverse news.
    Never follow symlinks and never remove unrelated files.
    """
    if not SYMBOL.fullmatch(symbol):raise EvidenceBlocked("BAD_REVOCATION_SYMBOL")
    target=output/(symbol+".json")
    if target.is_symlink():raise EvidenceBlocked("UNTRUSTED_CLEARANCE_SYMLINK")
    if target.exists():
        owner_protected(target)
        target.unlink()
        return True
    return False

def process(*,now=None,source=SOURCE,output=OUTPUT,gate=GATE,status=STATUS):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise EvidenceBlocked("CLOCK_NAIVE")
    now=now.astimezone(timezone.utc)
    try:g=json.loads(gate.read_text())
    except (OSError,ValueError):g=None
    if not holiday_allows(g,now):
        return {"status":"HOLIDAY_FAIL_CLOSED_NO_PUBLISH","files_published":0,"orders":0}
    owner_protected(source,directory=True)
    owner_protected(output,directory=True)
    published=0;blocked={};valid=set();revoked=[]
    files=list(sorted(source.glob("*.json")))
    if len(files)>300:raise EvidenceBlocked("TOO_MANY_SOURCE_BUNDLES")
    for path in files:
        if not SYMBOL.fullmatch(path.stem):
            blocked[path.name]="INVALID_SYMBOL_FILENAME";continue
        try:
            obj=safe_read(path)
            proof=eligible_bundle(path.stem,obj,now)
            atomic_write(output/(path.stem+".json"),proof)
            valid.add(path.stem)
            published+=1
        except (OSError,ValueError,TypeError,EvidenceBlocked) as ex:
            blocked[path.stem]=str(ex)[:100]
            if revoke_unqualified_proof(output,path.stem):
                revoked.append(path.stem)
    # Also revoke old signed symbols that were entirely absent from the latest
    # trusted source set. Do not rely merely on their 60-second expiry.
    existing=list(sorted(output.glob("*.json")))
    if len(existing)>300:raise EvidenceBlocked("TOO_MANY_OUTPUT_CLEARANCES")
    for previous in existing:
        if not SYMBOL.fullmatch(previous.stem):
            raise EvidenceBlocked("UNTRUSTED_OUTPUT_CLEARANCE_NAME")
        if previous.stem not in valid:
            if revoke_unqualified_proof(output,previous.stem):
                revoked.append(previous.stem)
    details=observed_coverage_gaps()
    publisher_status=("VERIFIED_CLEARANCE_PUBLISHED" if published else
        "WAITING_FOR_INDEPENDENT_SOURCE_BUNDLES" if not files else
        "SOURCE_ATTESTATIONS_REJECTED_OR_STALE")
    result={"status":publisher_status,
        "asof_utc":now.isoformat(),"source_bundles":len(files),
        "files_published":published,"blocked_count":len(blocked),
        "revoked_count":len(revoked),"revoked_symbols":revoked,
        "blocked_reasons_by_symbol":blocked,
        "source_gap_summary":details,"orders":0,
        "never_assume_missing_source_is_news_clear":True}
    # Diagnostic metadata is not a trusted BUY clearance, no account or raw data.
    if status:
        atomic_write(status,result)
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--once",action="store_true",required=True)
    args=parser.parse_args()
    print(json.dumps(process(),sort_keys=True))
