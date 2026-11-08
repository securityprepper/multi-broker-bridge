from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from multi_broker_bridge.five_day_rebound import Candle, evaluate, five_day_regime


def _data(down=True):
    z=Decimal
    first = [z("100"),z("99"),z("98"),z("97"),z("96"),z("95")] if down else [z("100"),z("101"),z("102"),z("103"),z("104"),z("105")]
    return {s:first[:] for s in ("AMD","MU","SNDK","SOXX")}


def _bars():
    end=datetime(2026,11,5,19,15,tzinfo=timezone.utc)
    out={}
    for symbol in ("AMD","MU","SNDK","SOXX"):
        # earlier 15m close -> latest gain 0.95%; last price breaks previous candle high
        out[symbol]=[
            Candle(end-timedelta(minutes=15),Decimal("99.5"),Decimal("99.0")),
            Candle(end-timedelta(minutes=10),Decimal("100.0"),Decimal("99.4")),
            Candle(end-timedelta(minutes=5),Decimal("100.3"),Decimal("100.0")),
            Candle(end,Decimal("101.2"),Decimal("101.0")),
        ]
    return out


def test_five_completed_sessions_excludes_today():
    regime,changes=five_day_regime(_data())
    assert regime=="down"
    assert changes["SOXX"] == Decimal("-0.05")


def test_buy_signal_requires_prior_downtrend():
    closes=_data()
    bars=_bars()
    prior={s:Decimal("99.0") for s in bars}
    result=evaluate(closes,prior,bars)
    assert result.qualifies
    assert result.prior_five=="down"
    assert result.reason=="BUY_WATCH"
    assert not evaluate(_data(False),prior,bars).qualifies


def test_fails_on_misaligned_missing_stale_bar():
    closes=_data();bars=_bars()
    bar=bars["MU"][-1]
    bars["MU"][-1]=Candle(bar.timestamp-timedelta(minutes=5),bar.high,bar.close)
    with pytest.raises(ValueError,match="misaligned"):
        evaluate(closes,{s:Decimal("99") for s in bars},bars)


def test_fails_when_15min_momentum_does_not_confirm():
    closes=_data();bars=_bars()
    for s in ("AMD","MU","SNDK"):
        first=bars[s][0]
        bars[s][0]=Candle(first.timestamp,first.high,Decimal("100.9"))
    output=evaluate(closes,{s:Decimal("99") for s in bars},bars)
    assert not output.qualifies
    assert "15min_momentum" in output.reason


def test_does_not_accept_empty_short_history():
    with pytest.raises(ValueError,match="exactly six"):
        five_day_regime({"AMD":[1]*5})


def test_requires_breakout_above_prior_high():
    closes=_data();bars=_bars()
    for s in ("AMD","MU","SNDK"):
        bar=bars[s][-2]
        bars[s][-2]=Candle(bar.timestamp,Decimal("102.0"),bar.close)
    output=evaluate(closes,{s:Decimal("99") for s in bars},bars)
    assert not output.qualifies
    assert "breakout" in output.reason
