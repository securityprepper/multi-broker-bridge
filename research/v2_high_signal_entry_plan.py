"""V2 RESEARCH-ONLY protected PAPER proposal generator. Produces NO orders."""
from dataclasses import dataclass
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from math import floor
from statistics import median

CHI=ZoneInfo("America/Chicago")

@dataclass(frozen=True)
class Catalyst:
    symbol: str
    category: str
    published_at: datetime
    first_seen_at: datetime
    material_bullish_verified: bool
    official_source_verified: bool

@dataclass(frozen=True)
class Quote:
    observed_at: datetime
    bid: float
    ask: float
    previous_close: float
    first_reaction_reference: float
    prior5_abs_daily_pct: tuple[float,...]

@dataclass(frozen=True)
class PaperAccount:
    label: str
    broker_environment: str
    broker_verified_at: datetime
    buying_power: float
    owned_symbols: tuple[str,...] = ()
    open_order_symbols: tuple[str,...] = ()
    stop_controller_verified: bool = False
    risk_cap_usd: float = 60.0

def plan(catalyst:Catalyst,quote:Quote,account:PaperAccount,now:datetime,
         session:str,forward_accuracy_verified:bool=False):
    """Return a proposal only. No broker API/client is imported or called."""
    bad=lambda why:{"status":"BLOCKED","reason":why,"order_submitted":False}
    if now.tzinfo is None or any(t.tzinfo is None for t in
         (catalyst.published_at,catalyst.first_seen_at,quote.observed_at,account.broker_verified_at)):
        return bad("naive timestamp")
    if account.broker_environment != "PAPER":
        return bad("account is not broker-confirmed PAPER")
    if (now-account.broker_verified_at).total_seconds()>120 or (
            now-quote.observed_at).total_seconds()>30:
        return bad("stale broker/quote readback")
    if catalyst.category not in ("EARNINGS_RELEASE_CANDIDATE_UNVERIFIED",
                                 "POSITIVE_NEWS_CANDIDATE_UNVERIFIED"):
        return bad("not a released material positive catalyst")
    if not(catalyst.material_bullish_verified and catalyst.official_source_verified):
        return bad("bullish source and implications not independently verified")
    if (now-catalyst.first_seen_at).total_seconds()>180 or catalyst.published_at>now:
        return bad("news late or from the future")
    if quote.observed_at<catalyst.first_seen_at:
        return bad("quote predates observed news")
    if quote.bid<=0 or quote.ask<quote.bid or quote.previous_close<=0 or quote.first_reaction_reference<=0:
        return bad("invalid executable quote")
    if len(quote.prior5_abs_daily_pct)!=5 or any(x<0 for x in quote.prior5_abs_daily_pct):
        return bad("missing five COMPLETED preceding days")
    price=(quote.bid+quote.ask)/2
    spread_pct=100*(quote.ask-quote.bid)/price
    if spread_pct>(0.5 if session=="RTH" else 1.0):
        return bad("wide bid-ask spread")
    if price<=quote.previous_close*1.0025:
        return bad("not clearly rising relative to prior close")
    # Require a fresh rally, not price miles beyond as-of initial news reaction.
    allowed_extension=min(3.0,max(1.5,median(quote.prior5_abs_daily_pct)))
    if 100*(quote.ask/quote.first_reaction_reference-1)>allowed_extension:
        return bad("already extended after catalyst")
    if catalyst.symbol in account.owned_symbols or catalyst.symbol in account.open_order_symbols:
        return bad("existing or pending same-symbol PAPER exposure")
    if session not in ("RTH","EXTENDED"):
        return bad("unsupported session")
    if session=="EXTENDED" and not account.stop_controller_verified:
        return bad("overnight software stop not independently commissioned")
    ct=now.astimezone(CHI)
    if session=="RTH" and ct.hour*60+ct.minute>=13*60+15:
        return bad("too late to guarantee 2pm Chicago flat objective")
    if not forward_accuracy_verified:
        return bad("no independently validated post-news after-cost predictive edge")
    limit=round(quote.ask*(1+0.001),2)
    stop_pct=min(4.0,max(2.5,1.25*median(quote.prior5_abs_daily_pct)))
    by_notional=floor(2000/limit)
    by_funds=floor(max(0,account.buying_power)/limit)
    by_risk=floor(account.risk_cap_usd/(limit*stop_pct/100))
    qty=min(by_notional,by_funds,by_risk)
    if qty<1:return bad("one whole share exceeds notional, funds or risk cap")
    stop=round(limit*(1-stop_pct/100),2)
    target=round(limit*(1+1.5*stop_pct/100),2)
    return {"status":"PAPER_PROPOSAL_REQUIRES_COMMISSIONED_EXECUTOR",
            "symbol":catalyst.symbol,"account":account.label,"qty":qty,
            "limit":limit,"profit_target":target,"stop":stop,
            "notional":round(qty*limit,2),"estimated_hard_stop_risk":round(qty*(limit-stop),2),
            "session":session,"stop_type":"NATIVE_BROKER_BRACKET" if session=="RTH" else "VERIFIED_SOFTWARE_STOP",
            "order_submitted":False}
