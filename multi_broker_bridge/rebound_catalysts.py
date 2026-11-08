"""Causal earnings/guidance catalyst risk filter for semiconductor rebound trades.

This filter is intentionally narrow: it looks only for independently
timestamped, explicitly named AMD/MU/SNDK adverse company-fundamental
headlines. Generic 'chip stocks are down' reporting is NOT a veto; an
overnight recovery can follow a broadly bearish sector story.

No broker access, network calls or order submission in this module.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import re
from typing import Iterable, Mapping

ANCHORS={
    "AMD": re.compile(r"\b(?:AMD|Advanced Micro Devices|Lisa Su)\b",re.I),
    "MU": re.compile(r"\b(?:Micron|MU)\b",re.I),
    "SNDK": re.compile(r"\b(?:Sandisk|SanDisk|SNDK)\b",re.I),
}
NEGATIVE=re.compile(
    r"\b(?:miss(?:es|ed)?|cut(?:s)?|lower(?:s|ed)?|slip(?:s|ped)?|"
    r"plunge(?:s|d)?|crater(?:s|ed)?|rout|selloff|sell-off|"
    r"worr(?:y|ies)|doubt(?:s)?|disappoint(?:s|ed)?|warning|"
    r"downgrade|weakness|weak|down(?:turn)?|drop(?:s|ped)?)\b",re.I)
MATERIAL=re.compile(
    r"\b(?:earnings|forecast|guidance|outlook|quarter|results|"
    r"revenue|China|licens(?:e|ing)|sales)\b",re.I)


def parse_time(value):
    if not isinstance(value,str):
        raise ValueError("news timestamp unavailable")
    instant=datetime.fromisoformat(value.replace("Z","+00:00"))
    if instant.tzinfo is None:
        raise ValueError("news timestamps must be timezone-aware")
    return instant.astimezone(timezone.utc)


def screen(articles:Iterable[Mapping],asof:datetime,window:timedelta=timedelta(hours=24),
           minimum_distinct:int=2):
    """Return a deterministic anchor-specific veto only with >=2 distinct headlines.

    Require explicit company name/ticker IN the headline, negative context,
    company fundamentals context, created and latest-updated BEFORE evaluation.
    A provider revision after evaluation is excluded rather than backdated.
    """
    if asof.tzinfo is None or minimum_distinct<1:
        raise ValueError("invalid decision time or threshold")
    now=asof.astimezone(timezone.utc)
    matched={s:set() for s in ANCHORS}
    visible_counts={s:0 for s in ANCHORS}
    for article in articles:
        if not isinstance(article,Mapping):
            raise ValueError("malformed historical news article")
        created=parse_time(article.get("created_at"))
        updated=parse_time(article.get("updated_at",article["created_at"]))
        if not now-window<=created<=now or updated>now:
            continue
        headline=article.get("headline")
        if not isinstance(headline,str) or not headline.strip():
            continue
        for symbol,pattern in ANCHORS.items():
            if pattern.search(headline):
                visible_counts[symbol]+=1
                if NEGATIVE.search(headline) and MATERIAL.search(headline):
                    matched[symbol].add(re.sub(r"\W+"," ",headline.casefold()).strip())
    severe={s:len(items) for s,items in matched.items() if len(items)>=minimum_distinct}
    return {
        "veto":bool(severe),
        "affected_anchors":tuple(sorted(severe)),
        "distinct_adverse_company_headlines":severe,
        "company_headlines_seen":visible_counts,
        "asof_utc":now.isoformat(),
    }
