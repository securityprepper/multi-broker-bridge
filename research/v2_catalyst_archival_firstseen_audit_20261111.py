"""Audit historical Alpaca news metadata without disclosing licensed articles.

Historical archive is a *retrospective fetch*, not contemporaneous evidence of
when the system first received each article. created_at is publisher time;
updated_at is revision time; neither is an observed_at broker/research receipt.
Never conclude forward availability without recorded first_observed_at.
Pure offline reading, no network, brokers, orders, messages or timers.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import json

def parse(s):
    if not isinstance(s,str):raise ValueError("missing timestamp")
    t=datetime.fromisoformat(s.replace("Z","+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:raise ValueError("naive timestamp")
    return t.astimezone(timezone.utc)

def summarize_articles(rows):
    c=Counter()
    for r in rows:
        if not isinstance(r,dict):continue
        c["articles"]+=1
        try:
            created=parse(r["created_at"]);updated=parse(r["updated_at"])
            lag=(updated-created).total_seconds()
            if lag<0:c["reversed_publication_update"]+=1
            if lag>0:c["modified_after_creation"]+=1
            if lag>300:c["modified_over_5m"]+=1
            if lag>3600:c["modified_over_1h"]+=1
        except (KeyError,ValueError,TypeError):
            c["invalid_publication_update_time"]+=1
        if "first_observed_at" not in r and "first_observed_at_utc" not in r:
            c["no_contemporaneous_first_seen"]+=1
        if not {"official_issuer_cik","numeric_previous_guidance","numeric_new_guidance",
                "issuer_release_evidence_url"}<=set(r):
            c["no_verified_numeric_issuer_guidance"]+=1
        if not {"independent_analyst_old_estimate","independent_analyst_new_estimate",
                "independent_analyst_publication_utc"}<=set(r):
            c["no_independent_numeric_estimate_revision"]+=1
    return dict(c)

def summarize_triggering_versions(evaluations,by_id):
    c=Counter()
    for row in evaluations:
        if row.get("status")!="POSITIVE_RESEARCH":continue
        c["positive_evaluations"]+=1
        at=parse(row["evaluation_time_et"])
        for trigger in row.get("triggering_articles",[]):
            c["triggering_article_joins"]+=1
            article=by_id.get(str(trigger.get("id")))
            if article is None:
                c["missing_raw_article_id"]+=1;continue
            c["article_ids_matched"]+=1
            try:
                created=parse(article["created_at"]);updated=parse(article["updated_at"])
                if updated>created:c["final_record_updated_after_creation"]+=1
                if created>at:c["created_after_decision"]+=1
                if updated>at:c["final_record_updated_after_decision"]+=1
            except (KeyError,ValueError,TypeError):
                c["bad_trigger_time"]+=1
            if not article.get("first_observed_at") and not article.get("first_observed_at_utc"):
                c["no_forward_own_first_seen_at_signal"]+=1
    return dict(c)

def audit_directory(folder,optional_eval=None):
    directory=Path(folder)
    if not directory.is_dir():raise ValueError("archive directory unavailable")
    all_rows=[];by_id={};files=0
    for f in sorted(directory.glob("*.json")):
        obj=json.loads(f.read_text())
        if not isinstance(obj,dict) or obj.get("complete") is not True:
            raise ValueError("archive incomplete")
        rows=obj.get("articles",[])
        if not isinstance(rows,list):raise ValueError("archive malformed")
        files+=1
        for row in rows:
            if not isinstance(row,dict):raise ValueError("article malformed")
            all_rows.append(row);by_id[str(row.get("news_id"))]=row
    summary={"archive_files":files,"article_metadata":summarize_articles(all_rows),
             "unique_ids":len(by_id),"research_only":True,"broker_calls":0,
             "observed_data_not_sufficient_for_trading":True}
    if optional_eval is not None:
        eval_rows=json.loads(Path(optional_eval).read_text())
        if not isinstance(eval_rows,list):raise ValueError("evaluation rows malformed")
        summary["positive_history"]=summarize_triggering_versions(eval_rows,by_id)
    return summary
