"""Real upstream GET-only SEC + issuer RSS + entitled Alpaca news collector.

Produces a protected source bundle for the separate root publisher ONLY after
verifying all three independently fetched original response versions. It NEVER
issues orders, clears its own attestation, or assumes absence = clean.
Ambiguous headlines, any new material filing, provider gaps or missing feed
coverage are REVIEW/NO BUY. Unrelated issuers cannot be used as clean evidence.

NOTE: currently supports only explicitly verified issuer feeds AMD/INTC/NVDA.
Other symbols fail closed. To add one, verify an original issuer-owned feed
with a complete lookback and add to this fixed allowlist with tests.
"""
from __future__ import annotations
import argparse,datetime as dt,email.utils,hashlib,json,os,re,sqlite3,stat,tempfile,gzip
from pathlib import Path
from urllib.parse import urlencode,urlparse
from urllib.request import Request,build_opener,HTTPRedirectHandler
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
from recommendation_paper_bridge.news_eligibility import (
    CATEGORIES, yesterday_today_start
)
from recommendation_paper_bridge.news_clearance_publisher import (
    holiday_allows,owner_protected,atomic_write,when,EvidenceBlocked
)

SEC_BASE="https://data.sec.gov/submissions/CIK"
ALPACA_BASE="https://data.alpaca.markets/v1beta1/news"
ISSUER_RSS={
    "AMD":("https://ir.amd.com/news-events/press-releases/rss","ir.amd.com"),
    "INTC":("https://www.intc.com/news-events/press-releases/rss","www.intc.com"),
    "NVDA":("https://nvidianews.nvidia.com/rss.xml","nvidianews.nvidia.com"),
    "FTV":("https://investors.fortive.com/news-events/press-releases/rss","investors.fortive.com"),
    "MRVL":("https://investor.marvell.com/news-events/press-releases/rss","investor.marvell.com"),
    "FROG":("https://investors.jfrog.com/rss/pressrelease.aspx","investors.jfrog.com")
}
CIK_MAP=Path("/var/lib/securityprepper-earnings-watch-v1/sec-ticker-ids.json")
CREDENTIALS=Path("/etc/securityprepper/alpaca-feed/private")
HOLIDAY_GATE=Path("/var/lib/securityprepper-v2-forward-shadow/holiday_gate.json")
OUTPUT=Path("/etc/securityprepper/recommendation-paper-bridge/news-source-proofs")
STATUS=Path("/var/lib/securityprepper-news-source-collector/status.json")
ARCHIVE=Path("/var/lib/securityprepper-news-source-collector/evidence")
SQLITE=Path("/var/lib/securityprepper-quality-watch/state.sqlite3")
UA="SecurityPrepper Investor News Research research@securityprepper.com"
MAX_BYTES=3_000_000

class SourceUnknown(ValueError):
    def __init__(self,reason):self.reason=reason;super().__init__(reason)

class RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise SourceUnknown("SOURCE_REDIRECT_NOT_ATTESTED")

def bytes_sha(raw):return hashlib.sha256(raw).hexdigest()
def document_hash(obj):
    return bytes_sha(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())

def archive_raw_response(blob,root=ARCHIVE):
    """Persist exact GET bytes by SHA with private, compressed content-addressing.

    This archive does NOT certify future price/news availability; the first
    received timestamp in the signed source manifest remains actual GET time.
    """
    if not root.is_dir() or root.is_symlink():
        raise SourceUnknown("RECEIPT_ARCHIVE_NOT_ROOT_PROTECTED")
    st=root.stat()
    if st.st_uid!=0 or st.st_mode & 0o077:
        raise SourceUnknown("RECEIPT_ARCHIVE_NOT_ROOT_PROTECTED")
    name=bytes_sha(blob)+".gz"
    path=root/name
    if path.is_symlink():raise SourceUnknown("RECEIPT_ARCHIVE_UNTRUSTED_SYMLINK")
    if path.exists():
        with gzip.open(path,"rb") as f:stored=f.read(MAX_BYTES+1)
        if stored!=blob:raise SourceUnknown("RECEIPT_ARCHIVE_HASH_MISMATCH")
        return name
    data=gzip.compress(blob,compresslevel=6,mtime=0)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,"wb") as h:
        h.write(data);h.flush();os.fsync(h.fileno())
    os.chown(path,0,0)
    return name

def received(now_clock):
    n=now_clock()
    if not isinstance(n,dt.datetime) or n.tzinfo is None:
        raise SourceUnknown("SOURCE_RECEIPT_TIMESTAMP_UNKNOWN")
    return n.astimezone(dt.timezone.utc)

def get(url,headers,expected_host,now_clock,opener=None):
    if (not url.startswith("https://") or urlparse(url).hostname!=expected_host
        or urlparse(url).username or urlparse(url).password):
        raise SourceUnknown("NOT_ALLOWLISTED_HTTPS_SOURCE")
    provider=opener or build_opener(RejectRedirect()).open
    with provider(Request(url,headers=headers,method="GET"),timeout=10) as res:
        if res.status!=200 or urlparse(res.url).hostname!=expected_host:
            raise SourceUnknown("SOURCE_STATUS_OR_HOST_MISMATCH")
        blob=res.read(MAX_BYTES+1)
    at=received(now_clock)
    if len(blob)==0 or len(blob)>MAX_BYTES:
        raise SourceUnknown("SOURCE_RESPONSE_MISSING_OR_OVERSIZE")
    archive_raw_response(blob)
    return blob,at

def sec_snapshot(symbol,cik,cutoff,now,clock,getfn=get):
    url=f"{SEC_BASE}{int(cik):010d}.json"
    raw,t=getfn(url,{"User-Agent":UA,"Accept":"application/json"},
                "data.sec.gov",clock)
    doc=json.loads(raw)
    if (int(doc.get("cik",0))!=int(cik) or not doc.get("name")
        or symbol not in doc.get("tickers",[])):
        raise SourceUnknown("SEC_CIK_TICKER_IDENTITY_MISMATCH")
    i=doc["tickers"].index(symbol)
    exchanges=doc.get("exchanges",[])
    if i>=len(exchanges):raise SourceUnknown("SEC_EXCHANGE_UNKNOWN")
    exchange=exchanges[i].upper()
    if "NASDAQ" in exchange: exchange="NASDAQ"
    elif "NYSE" in exchange or "NEW YORK" in exchange:exchange="NYSE"
    elif "AMEX" in exchange or "NYSE AMERICAN" in exchange:exchange="AMEX"
    else:raise SourceUnknown("SEC_EXCHANGE_NOT_SUPPORTED")
    records=doc["filings"]["recent"]
    count=len(records.get("form",[]))
    if count<1 or any(len(records.get(k,[]))!=count for k in ("form","acceptanceDateTime","accessionNumber")):
        raise SourceUnknown("SEC_RECENT_FILINGS_MALFORMED")
    events=[];oldest=None
    for j in range(count):
        rawtime=records["acceptanceDateTime"][j]
        stamp=dt.datetime.fromisoformat(rawtime)
        # SEC acceptanceDateTime lacks offset; EDGAR officially timestamps ET.
        if stamp.tzinfo is None: stamp=stamp.replace(tzinfo=ZoneInfo("America/New_York"))
        stamp=stamp.astimezone(dt.timezone.utc)
        oldest=stamp if oldest is None else min(oldest,stamp)
        if cutoff<=stamp<=now:
            form=records["form"][j]
            acc=records["accessionNumber"][j]
            if not re.fullmatch(r"\d{10}-\d{2}-\d{6}",acc):
                raise SourceUnknown("SEC_ACCESSION_INVALID")
            if form.startswith(("8-K","6-K","10-K","10-Q","S-1","S-3","424","F-1","F-3")):
                events.append({"published_at":stamp.isoformat(),"category":
                    ("dilution" if form.startswith(("S-","424","F-")) else
                     "earnings" if form.startswith(("10-K","10-Q")) else "corporate_development"),
                    "status":"review_needed",
                    "source_reference":"SEC:"+acc,
                    "content_hash":document_hash({"form":form,"accession":acc,
                                                "items":records.get("items",[""]*count)[j]})})
            # Form 3/4/144 insider filings do NOT automatically imply new
            # company share dilution or material company-specific bad news.
    if oldest is None or oldest>cutoff:raise SourceUnknown("SEC_FILINGS_DO_NOT_COVER_YESTERDAY")
    return {"raw_sha256":bytes_sha(raw),"received":t,"exchange":exchange,
            "events":events,"name":doc["name"],"url":url,
            "oldest_filing_at":oldest}

def issuer_rss(symbol,cutoff,now,clock,getfn=get):
    try:url,host=ISSUER_RSS[symbol]
    except KeyError:raise SourceUnknown("UNSUPPORTED_OFFICIAL_ISSUER_RSS")
    raw,t=getfn(url,{"User-Agent":UA,"Accept":"application/rss+xml,application/xml"},host,clock)
    doc=ET.fromstring(raw)
    entries=doc.findall(".//item")
    if not (2<=len(entries)<=500):
        raise SourceUnknown("OFFICIAL_IR_RSS_EMPTY_OR_INVALID")
    events=[];oldest=None
    for e in entries:
        pub=e.findtext("pubDate")
        title=str(e.findtext("title") or "")
        link=str(e.findtext("link") or "")
        if not pub or not title or not link:
            raise SourceUnknown("ISSUER_RELEASE_TIME_OR_LINK_MISSING")
        time=email.utils.parsedate_to_datetime(pub)
        if time.tzinfo is None:raise SourceUnknown("ISSUER_RELEASE_PUBDATE_NAIVE")
        time=time.astimezone(dt.timezone.utc)
        oldest=time if oldest is None else min(oldest,time)
        if cutoff<=time<=now:
            if urlparse(link).scheme!="https" or urlparse(link).hostname!=host:
                # Some corporate links live on independently controlled
                # content hostnames. Untrusted target=>review, not clear.
                events.append({"published_at":time.isoformat(),"category":"corporate_development",
                  "status":"review_needed","source_reference":"ISSUER_RSS_URL_UNVERIFIED",
                  "content_hash":document_hash({"title":title,"link":link,"pubDate":pub})})
            else:
                # Current RSS headline/summary is not enough to certify
                # whether full press release contains adverse conditions.
                events.append({"published_at":time.isoformat(),"category":"corporate_development",
                   "status":"review_needed","source_reference":link,
                   "content_hash":document_hash({"title":title,"link":link,"pubDate":pub})})
    if oldest is None or oldest>cutoff:
        raise SourceUnknown("ISSUER_RSS_DOES_NOT_COVER_FULL_TWO_DAYS")
    return {"raw_sha256":bytes_sha(raw),"received":t,"events":events,
        "url":url,"oldest_release_at":oldest}

# No future/backfilled news knowledge is introduced: this is a deterministic,
# narrowly scoped *nonadverse* classification from actual issuer-specific,
# fully supplied licensed content. Everything else is REVIEW, never CLEAR.
PRICE_TARGET=re.compile(
    r"^.+? Adjusts (?P<issuer>[A-Za-z0-9 &.]+?) Price Target to \$(?P<to>[0-9]+(?:\.[0-9]+)?) from \$(?P<from>[0-9]+(?:\.[0-9]+)?)$",
    re.I
)
ADVERSE_WORDS=re.compile(
    r"\b(?:downgrad(?:e|es|ed)|fraud|bankrupt|lawsuit|material weakness|"
    r"restat(?:e|ement)|offering|dilut(?:e|ion)|guidance cut|guidance lower|"
    r"cut(?:s)? revenue forecast|miss(?:ed|es)? earnings|probe|"
    r"regulatory action|going concern|liquidity crisis)\b",re.I
)
BENZ_TARGET=re.compile(
    r"^(?P<firm>.+?) Maintains (?P<rating>Equal-Weight|Hold|Buy|Outperform|Overweight) on "
    r"(?P<issuer>[A-Za-z0-9 &.]+?), Raises Price Target to \$(?P<target>[0-9]+(?:\.[0-9]+)?)$",re.I
)
FISCAL_TARGET=re.compile(
    r"^(?P<firm>.+?) Maintains (?P<rating>Hold|Buy|Neutral|Outperform|Overweight) Rating "
    r"and Raises Price Target for (?P<issuer>[A-Za-z0-9 &.]+)$",re.I
)
def corroborated_positive_target(a,all_articles,issuer_main):
    """Only classify a maintained positive target raise when BOTH independent
    licensed syndicators agree on analyst, issuer, action and exact new target.
    The fiscal.ai full article must explicitly preserve prior rating.
    Single headline/no-content is never enough for this branch.
    """
    for benz in all_articles:
        if benz.get("source")!="benzinga":continue
        h=BENZ_TARGET.fullmatch(str(benz.get("headline") or "").strip())
        if not h or issuer_main.lower() not in h["issuer"].lower():continue
        for fiscal in all_articles:
            if fiscal.get("source")!="fiscal.ai":continue
            f=FISCAL_TARGET.fullmatch(str(fiscal.get("headline") or "").strip())
            if (not f or f["firm"].casefold()!=h["firm"].casefold() or
                issuer_main.lower() not in f["issuer"].lower()):
                continue
            txt=str(fiscal.get("content") or "").strip()
            if not txt or ADVERSE_WORDS.search(txt) or ADVERSE_WORDS.search(str(benz.get("headline"))):
                continue
            target=h["target"]
            # Fiscal note independently contains *the exact new target* and
            # the unchanged rating; no guessing old target amount.
            if (not re.search(r"raised its price target for "+re.escape(f["issuer"])+
                             r" to \$"+re.escape(target)+r"\b",txt,re.I) or
                not re.search(r"""maintain(?:ing|ed|s)? (?:its |the )?['"]?"""+
                              re.escape(f["rating"]) + r"""['"]? rating""",txt,re.I)):
                continue
            if str(a.get("id")) in (str(benz.get("id")),str(fiscal.get("id"))):
                return True
    return False

def classify_news_article(a,symbol,issuer_name,all_articles=None):
    headline=str(a.get("headline") or "").strip()
    content=str(a.get("content") or "").strip()
    issuer_short=re.sub(r"\b(?:CORPORATION|CORP|INC|INCORPORATED|PLC|LTD)\b","",
        issuer_name.upper()).strip(" .,")
    issuer_main=issuer_short.split()[0] if issuer_short else ""
    m=PRICE_TARGET.fullmatch(headline)
    if (a.get("source")=="fiscal.ai" and m and content and
        issuer_main and issuer_main.lower() in m["issuer"].lower() and
        not ADVERSE_WORDS.search(content) and not ADVERSE_WORDS.search(headline)
        and re.search(r"maintain(?:s|ed)? (?:its |the )?(?:equalweight|neutral|hold|buy|outperform|overweight) rating",content,re.I)):
        try:
            hi=float(m["to"]);lo=float(m["from"])
        except (TypeError,ValueError):hi=lo=0
        if 0<lo<hi:
            return ("analyst_upgrade","verified_nonadverse",
                    "LICENSED_NUMERIC_TARGET_RAISE_WITH_MAINTAINED_RATING")
    if (all_articles and issuer_main and
        corroborated_positive_target(a,all_articles,issuer_main)):
        return ("analyst_upgrade","verified_nonadverse",
                "TWO_LICENSED_SYNDICATORS_CORROBORATE_MAINTAINED_RATING_TARGET_RAISE")
    return ("corporate_development","review_needed",
            "MATERIALITY_OR_ISSUER_CAUSALITY_NOT_INDEPENDENTLY_ADJUDICATED")

def news_pages(symbol,cutoff,now,clock,credentials=CREDENTIALS,getfn=get,
               issuer_name=None):
    if not isinstance(symbol,str) or not re.fullmatch(r"[A-Z][A-Z0-9.]{0,11}",symbol):
        raise SourceUnknown("BAD_SYMBOL")
    cdir=Path(os.environ.get("CREDENTIALS_DIRECTORY",str(credentials)))
    if not cdir.is_dir() or cdir.is_symlink():raise SourceUnknown("NO_PROTECTED_ALPACA_CREDENTIALS")
    key=(cdir/"alpaca_data_key_id").read_text().strip()
    secret=(cdir/"alpaca_data_secret").read_text().strip()
    if not key or not secret:raise SourceUnknown("ALPACA_NEWS_ACCESS_NOT_CONFIGURED")
    headers={"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret,
             "Accept":"application/json"}
    params={"symbols":symbol,"start":cutoff.isoformat(),"end":now.isoformat(),
            "sort":"asc","limit":50,"include_content":"true"}
    tokens=set();token=None;news=[];hashes=[];last_observed=None
    for page in range(20):
        q=dict(params)
        if token:q["page_token"]=token
        url=ALPACA_BASE+"?"+urlencode(q)
        raw,t=getfn(url,headers,"data.alpaca.markets",clock)
        obj=json.loads(raw)
        if not isinstance(obj,dict) or not isinstance(obj.get("news"),list):
            raise SourceUnknown("LICENSED_NEWS_RESPONSE_SCHEMA_UNKNOWN")
        hashes.append(bytes_sha(raw));last_observed=t
        for a in obj["news"]:
            if not isinstance(a,dict) or symbol not in a.get("symbols",[]):
                raise SourceUnknown("LICENSED_NEWS_TICKER_SCOPE_NOT_PROVEN")
            item_id=str(a.get("id",""))
            if not item_id:raise SourceUnknown("LICENSED_NEWS_ID_MISSING")
            if not any(str(x.get("id"))==item_id for x in news):
                news.append(a)
        token=obj.get("next_page_token")
        if not token:break
        if not isinstance(token,str) or len(token)>512 or token in tokens:
            raise SourceUnknown("LICENSED_NEWS_PAGINATION_INVALID")
        tokens.add(token)
    else:
        raise SourceUnknown("LICENSED_NEWS_PAGINATION_EXCEEDED")
    if last_observed is None:raise SourceUnknown("LICENSED_NEWS_NOT_FETCHED")
    # Always use true GET completion receipt, never article original pubTime.
    # A neutral/positive headline is NOT independently proven nonadverse
    # merely because the title has no negative keywords; these require
    # source-content review before creating clean clearance.
    events=[]
    for a in news:
        try:published=when(a["created_at"])
        except Exception:raise SourceUnknown("NEWS_PUBLICATION_TIMESTAMP_UNKNOWN")
        if not cutoff<=published<=now:continue
        if a.get("source") not in ("benzinga","fiscal.ai"):
            raise SourceUnknown("UNRECOGNIZED_LICENSED_NEWS_ORIGIN")
        category,status,basis=classify_news_article(a,symbol,issuer_name or symbol,news)
        events.append({"published_at":published.isoformat(),"category":category,
            "status":status,"classification_basis":basis,
            "source_reference":"ALPACA_NEWS:"+str(a["id"]),
            "content_hash":document_hash(a)})
    return {"raw_sha256":document_hash(hashes),"original_response_shas":hashes,
        "received":last_observed,
        "events":events,"url":ALPACA_BASE,"pages":len(hashes),
        "article_count":len(news)}

def source_manifest(symbol,cik,now,clock,secfn=sec_snapshot,irfn=issuer_rss,newsfn=news_pages):
    cutoff=yesterday_today_start(now)
    official=secfn(symbol,cik,cutoff,now,clock)
    ir=irfn(symbol,cutoff,now,clock)
    licensed=newsfn(symbol,cutoff,now,clock,issuer_name=official["name"])
    if any(z["received"]>clock() for z in (official,ir,licensed)):
        raise SourceUnknown("FUTURE_RESPONSE_TIME")
    # Strict original receipt first-seen is what we actually retrieved.
    # Do NOT backdate live first_observed to historical publication.
    all_events=[]
    categories={
       "sec_edgar":set(["earnings","guidance","dilution","restatement","liquidity",
            "litigation","regulatory","corporate_development"]),
       "issuer_ir":set(["earnings","guidance","corporate_development"]),
       "licensed_news":set(CATEGORIES)}
    coverage=[];receipts={}
    for source,data in (("sec_edgar",official),("issuer_ir",ir),("licensed_news",licensed)):
        at=data["received"].astimezone(dt.timezone.utc).isoformat()
        ref=data["url"]
        digest=data["raw_sha256"]
        if not re.fullmatch("[0-9a-f]{64}",digest):raise SourceUnknown("EVIDENCE_SHA_INVALID")
        for e in data["events"]:
            # first-observed is source receipt; genuine old pub timestamp kept separately
            all_events.append({"symbol":symbol,"issuer_cik":f"{int(cik):010d}","source":source,
                "published_at":e["published_at"],"first_observed_at":at,
                "category":e["category"],"status":e["status"],
                "classification_basis":e.get("classification_basis","SOURCE_FACT_REQUIRES_REVIEW"),
                "source_reference":e["source_reference"],"content_hash":e["content_hash"]})
        coverage.append({"symbol":symbol,"issuer_cik":f"{int(cik):010d}","source":source,
          "verified_complete":True,"first_observed_at":at,
          "coverage_since":cutoff.isoformat(),
          "coverage_through":at,
          "source_reference":ref,"content_hash":digest,
          "categories":sorted(categories[source])})
        receipts[source]={"verified_original_snapshot":True,
         "provider_reference":ref,"original_receipt_sha256":digest,
         "original_response_shas":data.get("original_response_shas",[digest]),
         "received_at_utc":at,
         "coverage_since_utc":cutoff.isoformat(),
         "coverage_through_utc":at,
         "full_pagination_or_feed_coverage_proven":True}
    fresh=clock().astimezone(dt.timezone.utc)
    if fresh-now>dt.timedelta(minutes=1) or fresh<now:
        raise SourceUnknown("COLLECTOR_TIME_DRIFT")
    return {"schema_version":1,
      "source_scope":"COMPLETE_INDEPENDENT_YESTERDAY_TODAY_ISSUER_SEC_LICENSED_NEWS",
      "window_timezone":"America/Chicago","screening_start_utc":cutoff.isoformat(),
      "symbol":symbol,"exchange":official["exchange"],"issuer_cik":f"{int(cik):010d}",
      "fresh_collector_observed_at_utc":fresh.isoformat(),
      "identity":{"verified":True,"symbol":symbol,"exchange":official["exchange"],
        "issuer_cik":f"{int(cik):010d}","first_observed_at":official["received"].isoformat()},
      "coverage":coverage,"evidence":all_events,
      "independent_source_receipts":receipts}

def candidates(db=SQLITE):
    result=["FTV","AMD","INTC","NVDA","MRVL","FROG"]
    try:
        with sqlite3.connect("file:"+str(db)+"?mode=ro",uri=True,timeout=3) as conn:
            row=conn.execute("SELECT asof,signal_summary FROM scans ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            at=when(row[0])
            if dt.timedelta(0)<=dt.datetime.now(dt.timezone.utc)-at<=dt.timedelta(minutes=3):
                doc=json.loads(row[1])
                extras=[str(x) for x in doc.get("shortlist",[]) if x in ISSUER_RSS]
                result=list(dict.fromkeys(extras+result))
    except (OSError,ValueError,TypeError,sqlite3.Error,KeyError):
        pass
    return result[:6]

def run(now=None,clock=lambda:dt.datetime.now(dt.timezone.utc),source=OUTPUT,status=STATUS,
    holiday=HOLIDAY_GATE,ciks=CIK_MAP,chosen=None):
    now=now or clock()
    if now.tzinfo is None:raise SourceUnknown("NAIVE_RUN_TIME")
    now=now.astimezone(dt.timezone.utc)
    try:cache=json.loads(holiday.read_text())
    except (OSError,ValueError):cache=None
    if not holiday_allows(cache,now):
        return {"status":"HOLIDAY_FAIL_CLOSED","source_bundles_published":0,"broker_orders":0}
    # Don't attest a cached/unverified ticker directory. SEC submissions
    # independently re-verifies both the CIK and stock exchange.
    try:ids=json.loads(ciks.read_text())["symbols"]
    except (OSError,ValueError,KeyError):raise SourceUnknown("SEC_CIK_REFERENCE_NOT_AVAILABLE")
    owner_protected(source,directory=True)
    completed={}; errors={}
    for symbol in chosen if chosen is not None else candidates():
        if symbol not in ISSUER_RSS:errors[symbol]="OFFICIAL_IR_FEED_NOT_CONFIGURED";continue
        if symbol not in ids:errors[symbol]="SEC_IDENTITY_UNAVAILABLE";continue
        try:
            manifest=source_manifest(symbol,int(ids[symbol]),now,clock)
            if len(json.dumps(manifest))>250_000:
                raise SourceUnknown("SOURCE_BUNDLE_OVERSIZE")
            atomic_write(source/(symbol+".json"),manifest)
            completed[symbol]={"status":"SOURCE_BUNDLE_PUBLISHED",
               "evidence_count":len(manifest["evidence"]),
               "review_required":sum(e["status"]=="review_needed" for e in manifest["evidence"]),
               "source_receipts":3}
        except (SourceUnknown,EvidenceBlocked,TypeError,KeyError,ValueError,OSError,ET.ParseError) as e:
            errors[symbol]=getattr(e,"reason",type(e).__name__)
            # A previously valid proof is never left in place if the current
            # authenticated update fails.
            old=source/(symbol+".json")
            if old.is_file() and not old.is_symlink():old.unlink()
    done={"status":"UPSTREAM_SOURCE_COLLECTION_CHECKED",
      "asof_utc":clock().astimezone(dt.timezone.utc).isoformat(),
      "source_bundles_published":len(completed),"sources":completed,
      "blocked_sources":errors,"broker_orders":0,
      "news_classification":"STRICT_NONADVERSE_EVIDENCE_OR_FAIL_CLOSED_REVIEW",
      "clearance_published_by_collector":False}
    atomic_write(status,done)
    return done

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--once",action="store_true",required=True)
    args=ap.parse_args()
    print(json.dumps(run(),sort_keys=True))
