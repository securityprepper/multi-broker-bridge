"""Offline V2 directional sector score. Research only, no broker orders."""
from dataclasses import dataclass
from datetime import datetime
from math import sqrt

@dataclass(frozen=True)
class Forecast:
    sector: str
    date: str
    at: datetime
    last_complete_bar: datetime
    session_close_at: datetime
    side: str
    prior_close: float
    actual_close: float
    neutral_band_pct: float = 0.0

    def __post_init__(self):
        if self.side not in ("UP","DOWN","ABSTAIN"):
            raise ValueError("invalid prediction")
        if any(x.tzinfo is None for x in (self.at,self.last_complete_bar,self.session_close_at)):
            raise ValueError("naive timestamp")
        if not self.last_complete_bar <= self.at < self.session_close_at:
            raise ValueError("lookahead or uncompleted prediction")
        if self.prior_close <= 0 or self.actual_close <= 0 or self.neutral_band_pct < 0:
            raise ValueError("invalid price")
    @property
    def actual(self):
        change = 100*(self.actual_close/self.prior_close-1)
        return "UP" if change > self.neutral_band_pct else ("DOWN" if change < -self.neutral_band_pct else "NEUTRAL")

def lower_bound(correct,n):
    if not n:return 0.
    z=1.96;p=correct/n
    return (p+z*z/(2*n)-z*sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)

def evaluate(rows, min_days=30, target=.8):
    if len({(r.sector,r.date,r.at) for r in rows}) != len(rows):
        raise ValueError("duplicate time/sector")
    emitted=[r for r in rows if r.side!="ABSTAIN"]
    n=len(emitted); hits=sum(r.side==r.actual for r in emitted)
    precision={}
    recall={}
    for side in ("UP","DOWN"):
        pred=[r for r in emitted if r.side==side]
        actual=[r for r in rows if r.actual==side]
        precision[side]=sum(r.actual==side for r in pred)/len(pred) if pred else None
        recall[side]=sum(r.side==side for r in actual)/len(actual) if actual else None
    accuracy=hits/n if n else None
    balanced=[v for v in recall.values() if v is not None]
    days=len({r.date for r in emitted})
    return dict(forecasts=len(rows),issued=n,abstained=len(rows)-n,correct=hits,
                accuracy=accuracy,coverage=n/len(rows) if rows else 0,
                up_precision=precision["UP"],down_precision=precision["DOWN"],
                balanced_recall=sum(balanced)/len(balanced) if balanced else None,
                day_count=days,wilson95=lower_bound(hits,n),
                candidate_for_paper_shadow=bool(days>=min_days and accuracy is not None and accuracy>=target
                    and precision["UP"] is not None and precision["UP"]>=target
                    and precision["DOWN"] is not None and precision["DOWN"]>=target))
