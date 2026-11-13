"""Alpaca PAPER-only BUY preflight: authoritative issuer/news + completed last-5m direction.

This module only examines verified data; it never fetches broker orders,
submits an order, cancels a stop, changes positions or adds LIVE authority.
Protected issuer/SEC/licensed-news attestations must be root-owned and fresh.
No news coverage is NEVER interpreted as an absence of bad news.
"""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path
import stat
import sys

PROTECTED_BRIDGE_ROOT=Path("/opt/securityprepper/recommendation-paper-bridge")
FIVE_MINUTES=timedelta(minutes=5)
BAR_STEP=timedelta(minutes=1)
MAX_LAST_BAR_LAG=timedelta(seconds=135)
MAX_ORDER_CHECK_LAG=timedelta(seconds=45)

class PaperBuyBlocked(ValueError):
    def __init__(self,reason):
        self.reason=str(reason)
        super().__init__(self.reason)

def _positive_decimal(x):
    if type(x) is not Decimal or not x.is_finite() or x<=0:
        raise PaperBuyBlocked("PRICE_UNKNOWN_INVALID_DECIMAL")
    return x

def recent_five_minute_direction(symbol,bars,asof_utc,bid,ask):
    """Completed-bar-only, no intentional post-news delay, fail closed on stale gaps.

    Six 1-minute closes span FIVE consecutive minute-to-minute changes.
    Reject a falling latest close, negative five-minute change, or an
    executable bid below the oldest close. Do not rely on intrabar highs.
    """
    if (asof_utc.tzinfo is None or asof_utc.utcoffset() is None or
        not isinstance(symbol,str) or not symbol or symbol!=symbol.upper()):
        raise PaperBuyBlocked("PRICE_5M_IDENTITY_OR_CLOCK_UNKNOWN")
    bid=_positive_decimal(bid)
    ask=_positive_decimal(ask)
    if bid>ask:
        raise PaperBuyBlocked("PRICE_5M_BID_ASK_CROSSED")
    if not isinstance(bars,list) or len(bars)<6:
        raise PaperBuyBlocked("PRICE_5M_INSUFFICIENT_COMPLETED_BARS")
    now=asof_utc.astimezone(timezone.utc)
    recent=sorted(bars,key=lambda r:r.timestamp)[-6:]
    for b in recent:
        if b.symbol!=symbol or b.timestamp.tzinfo is None:
            raise PaperBuyBlocked("PRICE_5M_WRONG_OR_UNDATED_BAR")
        if b.timestamp+BAR_STEP>now:
            raise PaperBuyBlocked("PRICE_5M_INCOMPLETE_BAR")
        _positive_decimal(b.close)
    if not (timedelta(0)<=now-(recent[-1].timestamp+BAR_STEP)<=MAX_LAST_BAR_LAG):
        raise PaperBuyBlocked("PRICE_5M_STALE_COMPLETED_BAR")
    if any(b.timestamp-a.timestamp!=BAR_STEP for a,b in zip(recent,recent[1:])):
        raise PaperBuyBlocked("PRICE_5M_GAPPED_BARS")
    if recent[-1].timestamp-recent[0].timestamp!=FIVE_MINUTES:
        raise PaperBuyBlocked("PRICE_5M_WINDOW_NOT_5MIN")
    old,prev,latest=(recent[0].close,recent[-2].close,recent[-1].close)
    change=(latest/old-Decimal("1"))*Decimal("100")
    if latest<old or bid<old:
        raise PaperBuyBlocked("PRICE_5M_DECLINING_AVOID")
    if latest==old or bid==old:
        raise PaperBuyBlocked("PRICE_5M_FLAT_WATCH_ONLY")
    if latest<prev:
        raise PaperBuyBlocked("PRICE_5M_LAST_COMPLETED_BAR_FALLING")
    return {"status":"PRICE_5M_RISING_ASOF","five_minute_change_pct":str(change.quantize(Decimal("0.0001"))),
            "first_bar_at_utc":recent[0].timestamp.astimezone(timezone.utc).isoformat(),
            "last_completed_bar_at_utc":(recent[-1].timestamp+BAR_STEP).astimezone(timezone.utc).isoformat()}

def trusted_news_clearance(symbol,asof_utc):
    """Import the existing trusted root-attestation validator, not a weak headline scan.

    The fixed publisher path must remain root-controlled and non-writable by
    the executor; a missing/empty directory is NEWS_UNKNOWN and blocks BUY.
    """
    try:
        for p in (PROTECTED_BRIDGE_ROOT,PROTECTED_BRIDGE_ROOT/"recommendation_paper_bridge"):
            st=p.stat()
            if not stat.S_ISDIR(st.st_mode) or st.st_uid!=0 or st.st_mode&0o022:
                raise PaperBuyBlocked("NEWS_ATTESTOR_SOURCE_UNTRUSTED")
        root=str(PROTECTED_BRIDGE_ROOT)
        if root not in sys.path:sys.path.insert(0,root)
        from recommendation_paper_bridge.news_clearance import require_clear,NewsBlocked
        try:
            proof=require_clear(symbol,asof_utc)
        except NewsBlocked as exc:
            status=str(exc.status)
            if status in ("NEWS_MATERIAL_ADVERSE","NEWS_REVIEW_WATCH_ONLY"):
                raise PaperBuyBlocked("NEWS_ADVERSE_OR_REVIEW_AVOID") from exc
            raise PaperBuyBlocked("NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE") from exc
        if not isinstance(proof,dict) or proof.get("status")!="NEWS_CLEAR_ASOF" or not proof.get("evidence_sha256"):
            raise PaperBuyBlocked("NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE")
        return {"status":"NEWS_CLEAR_ASOF",
                "evidence_sha256":proof["evidence_sha256"],
                "issuer_cik":proof["issuer_cik"],
                "news_checked_at_utc":asof_utc.astimezone(timezone.utc).isoformat()}
    except PaperBuyBlocked:
        raise
    except (ImportError,AttributeError,OSError,TypeError,ValueError,KeyError):
        raise PaperBuyBlocked("NEWS_UNKNOWN_TRUSTED_ATTESTOR_UNAVAILABLE") from None

def require_mbb_buy_preflight(symbol,bars,asof_utc,bid,ask,news_check=trusted_news_clearance):
    """Two independent checks, both mandatory. NEWS status never inferred from bars."""
    if asof_utc.tzinfo is None or asof_utc.utcoffset() is None:
        raise PaperBuyBlocked("PAPER_BUY_CLOCK_UNKNOWN")
    # Independent issuer/SEC/news clearance is mandatory before considering
    # positive price momentum. A move UP can never clear missing bad-news data.
    news=news_check(symbol,asof_utc)
    if not isinstance(news,dict) or news.get("status")!="NEWS_CLEAR_ASOF":
        raise PaperBuyBlocked("NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE")
    direction=recent_five_minute_direction(symbol,bars,asof_utc,bid,ask)
    return {"status":"PAPER_BUY_PREFLIGHT_PASS","news_clearance":news,"direction":direction}
