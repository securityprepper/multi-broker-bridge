"""Research-only issuer-own-guidance attribution veto (no network, no orders).

This gate supplies conservative *headline plausibility*, never issuer verification.
A tagged symbol or positive Benzinga headline is insufficient to establish that
the named issuer improved its own EPS/revenue/growth guidance. Fail closed.
"""
import re

RAISE = re.compile(r"\b(raise[sd]?|raised|raising|boost(?:s|ed)?|lift(?:s|ed)?|hik(?:e|es|ed))\b", re.I)
OUTLOOK = re.compile(r"\b(guidance|outlook|forecast|revenue (?:growth )?expectations)\b", re.I)
NON_EARNINGS = re.compile(
    r"\b(price target|price forecast|target price|analyst|capex|capital expenditures?|"
    r"capital spending|dividend|buyback|repurchase)\b", re.I
)
CONTEXT = re.compile(r"\b(as|after|amid|because|following|rival|peer|competitor)\b", re.I)

def own_guidance_headline(headline, aliases):
    """Only potential direct company EPS/sales/growth guidance revision.

    aliases are independently verified issuer names, NOT article symbols[].
    Returns (bool, reason). True is NOT authorization: separate primary issuer
    document, its publication time, numeric revision and news veto are required.
    """
    if not isinstance(headline,str) or not headline.strip():
        return False,"BAD_HEADLINE"
    if not aliases or not all(isinstance(a,str) and len(a.strip())>=3 for a in aliases):
        return False,"MISSING_VERIFIED_ISSUER_MAPPING"
    h=" ".join(headline.split())
    raise_match=RAISE.search(h)
    outlook_match=OUTLOOK.search(h)
    if not raise_match or not outlook_match:
        return False,"NO_GUIDANCE_REVISION"
    if NON_EARNINGS.search(h):
        return False,"NOT_DIRECT_EARNINGS_GUIDANCE"
    # The issuer must be explicit in the initial grammatical subject.
    # Never trust an article's symbols[] to infer subject of a later "raises".
    prefix=h[:raise_match.start()]
    found=False
    for a in aliases:
        nm=re.escape(a.strip())
        if re.match(r"^"+nm+r"\b", h,flags=re.I):
            found=True
            break
    if not found:return False,"ISSUER_NOT_INITIAL_SUBJECT"
    if CONTEXT.search(prefix):
        return False,"SECONDARY_COMPANY_CONTEXT"
    # Keep ambiguous report language separate from issuer-verified numeric facts.
    return True,"PLAUSIBLE_OWN_GUIDANCE_UNVERIFIED"

def audit_triggering_articles(rows, alias_by_ticker):
    """Evaluate distinct positive-guidance article+symbol pairs from frozen rows."""
    seen=set()
    counts={}
    flagged=[]
    for row in rows:
        if row.get("status")!="POSITIVE_RESEARCH":continue
        symbol=row.get("symbol")
        for item in row.get("triggering_articles",[]):
            if "GUIDANCE_RAISE_HEADLINE" not in item.get("labels",[]):continue
            key=(str(symbol),str(item.get("id")))
            if key in seen:continue
            seen.add(key)
            ok,reason=own_guidance_headline(item.get("headline",""),alias_by_ticker.get(symbol,[]))
            counts[reason]=counts.get(reason,0)+1
            if not ok:flagged.append({"symbol":symbol,"news_id":item.get("id"),"reason":reason})
    return {"distinct_guidance_symbol_article_pairs":len(seen),
            "reason_counts":counts,"flagged":sorted(flagged,key=lambda x:(x["symbol"],str(x["news_id"]))),
            "not_orders":True,"unverified_issuer":True}
