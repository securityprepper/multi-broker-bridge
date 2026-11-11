"""Bounded official SEC Form 4 XML research pilot; no broker API/quotes/orders.

Only official SEC GET. No service installation, background polling, notifications.
The provided historical accepted-at time is NOT evidence of our original first-seen.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

MODULE = Path(__file__).with_name("v2_form4_insider_purchase_pit_gate_20261111.py")
spec = importlib.util.spec_from_file_location("pilot_form4", MODULE)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
UA = "SecurityPrepper public EDGAR research home@securityprepper.com"
SYMBOLS = ("AMD","MU","NVDA","CAT","GS","JPM","BAC","CRWD","PANW",
           "MSFT","XOM","CVX","UNH","LLY","PEP","ACN","SBUX")
CUT = datetime(2026,11,11,13,40,tzinfo=timezone.utc)
MAX_PER_ISSUER = 3
SEC_ROOT = "https://www.sec.gov"
DSEC_ROOT = "https://data.sec.gov"


def get(url):
    time.sleep(.53)  # well under SEC published fair-access rate
    req=Request(url,headers={"User-Agent":UA, "Accept":"application/json,application/xml,text/xml"})
    with urlopen(req,timeout=12) as f:
        if f.status != 200:
            raise ValueError("unexpected HTTP status")
        return f.read(3_000_000)


def public_ticker_map():
    raw=json.loads(get(SEC_ROOT+"/files/company_tickers.json"))
    return {d["ticker"].upper():str(d["cik_str"]) for d in raw.values()}


def form4_list(sub,cut= CUT):
    recent=sub["filings"]["recent"]
    out=[]
    for i,form in enumerate(recent["form"]):
        if form != "4":continue
        accepted=mod.timestamp(recent["acceptanceDateTime"][i])
        if accepted is None or accepted>cut: continue
        accession=recent["accessionNumber"][i]
        doc=recent["primaryDocument"][i]
        if not re.fullmatch(r"\d{10}-\d\d-\d{6}",accession):continue
        if not re.fullmatch(r"[A-Za-z0-9._/-]+",doc):continue
        out.append({"accession":accession,"accepted_utc":recent["acceptanceDateTime"][i],
                    "filename":doc.rsplit("/",1)[-1]})
    return out


def run():
    tickers=public_ticker_map()
    all_results=[]
    summary={"research_only":True,"captured_at_utc":datetime.now(timezone.utc).isoformat(),
             "cutoff_at_utc":CUT.isoformat(),"source":"Official SEC submissions and Form 4 XML",
             "historical_first_seen_observed":False,"submit_orders":False,
             "max_recent_original_form4_per_issuer":MAX_PER_ISSUER,
             "symbols_requested":list(SYMBOLS),"issuer_results":{},
             "representative_events":[],"scope_limits":
             ["Issuer recent submissions only; no reporting-owner universe or amended historical files",
              "Last three original Form 4 filings per sampled issuer, not a complete market scan",
              "No contemporaneous first-observed historical collector timestamps",
              "No SIP/NBBO quote entry, fills, commissions, matched controls or forward P&L"]}
    for sym in SYMBOLS:
        issuer={"ticker":sym,"cik":tickers.get(sym),"form4_in_recent_submission_array":0,
                "xml_attempted":0,"xml_parsed":0,"strict_qualified_without_first_seen":0,
                "reasons":{},"errors":[]}
        summary["issuer_results"][sym]=issuer
        if issuer["cik"] is None:
            issuer["errors"].append("CIK_UNRESOLVED");continue
        try:
            sub=json.loads(get(f"{DSEC_ROOT}/submissions/CIK{int(issuer['cik']):010d}.json"))
            filings=form4_list(sub)
            issuer["form4_in_recent_submission_array"]=len(filings)
            for x in filings[:MAX_PER_ISSUER]:
                accession=x["accession"]; base=accession.replace("-","")
                url=f"{SEC_ROOT}/Archives/edgar/data/{int(issuer['cik'])}/{base}/{x['filename']}"
                issuer["xml_attempted"]+=1
                try:
                    xml=get(url)
                    out=mod.evaluate_form4(xml,expected_issuer_cik=issuer["cik"],
                        accession=accession,sec_accepted_at=x["accepted_utc"],
                        first_observed_at=None,
                        decision_at=CUT.isoformat(),expected_symbol=sym)
                    issuer["xml_parsed"]+=1
                    if out.flagged_open_market_purchase and not any(
                        r for r in out.reasons if r != "MISSING_ORIGINAL_FIRST_SEEN"):
                        issuer["strict_qualified_without_first_seen"]+=1
                    for reason in out.reasons:
                        issuer["reasons"][reason]=issuer["reasons"].get(reason,0)+1
                    summary["representative_events"].append({
                        "ticker":sym,"accession":accession,"accepted_utc":x["accepted_utc"],
                        "content_sha256":out.content_sha256,
                        "direct_purchase_usd":out.direct_purchased_usd,
                        "screen_decision":out.decision,"reasons":list(out.reasons),
                        "never_trade":not out.allowed_to_trade})
                except (HTTPError,URLError,TimeoutError,ValueError) as exc:
                    issuer["errors"].append("XML_GET_FAILED_"+type(exc).__name__)
        except (HTTPError,URLError,TimeoutError,ValueError,KeyError,TypeError) as exc:
            issuer["errors"].append("ISSUER_GET_FAILED_"+type(exc).__name__)
        print(sym,{"recent":issuer["form4_in_recent_submission_array"],
                   "parsed":issuer["xml_parsed"],
                   "strict_without_firstseen":issuer["strict_qualified_without_first_seen"],
                   "errors":issuer["errors"]},flush=True)
    summary["totals"]={"issuers_attempted":len(SYMBOLS),
        "form4_metadata_rows_sampled":sum(x["form4_in_recent_submission_array"] for x in summary["issuer_results"].values()),
        "xml_read":sum(x["xml_parsed"] for x in summary["issuer_results"].values()),
        "strict_without_firstseen":sum(x["strict_qualified_without_first_seen"] for x in summary["issuer_results"].values()),
        "valid_live_trade_signals":0}
    Path("/tmp/v2-form4-sec-public-pilot-20261111.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print("SUMMARY",summary["totals"],flush=True)
if __name__=="__main__":run()