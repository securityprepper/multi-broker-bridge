"""Read-only pending Recommendation Audit export plus durable closed watermark.

A position is eligible for a user-facing audit ONLY after matched Alpaca
parent+exit FILL activities show it closed. Do not report open/unfilled cases.
"""
from __future__ import annotations
import argparse,json,re
from .bridge import db_connect,Unsafe
DB="securityprepper_trading"
INTENTS=DB+".sp_paper_rec_intents"
EVENTS=DB+".sp_paper_rec_events"
WATERMARK=DB+".sp_paper_rec_audit_watermarks"

def pending(connect=db_connect):
    conn=connect("PAPER_BRIDGE_AUDIT_CNF")
    try:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT e.id AS event_id,e.recommendation_id,e.evidence_json,"
            "i.source_task,i.source_run_id,i.symbol,i.issued_at_utc,i.quote_at_utc,"
            "i.quote_last,i.quote_bid,i.quote_ask,i.action,i.limit_price,"
            "i.profit_target,i.stop_loss,i.rationale,i.intended_qty,i.client_order_id,"
            "i.broker_order_id,i.status AS bridge_status "+
            "FROM "+EVENTS+" e JOIN "+INTENTS+" i ON i.recommendation_id=e.recommendation_id "+
            "LEFT JOIN "+WATERMARK+" w ON w.recommendation_id=e.recommendation_id "+
            "WHERE e.event_type='BROKER_FILL_READBACK' AND "+
            "JSON_UNQUOTE(JSON_EXTRACT(e.evidence_json,'$.state'))='CLOSED_NEEDS_FEE_RECON' "+
            "AND w.recommendation_id IS NULL ORDER BY e.id DESC LIMIT 200")
        rows=cur.fetchall()
        seen=set();out=[]
        for x in rows:
            if x["recommendation_id"] in seen:continue
            seen.add(x["recommendation_id"])
            evidence=x.pop("evidence_json")
            if isinstance(evidence,str):evidence=json.loads(evidence)
            if evidence.get("state")!="CLOSED_NEEDS_FEE_RECON":
                continue
            if not evidence.get("fill_activity_ids") or not evidence.get("exit_at"):
                continue
            for k,v in list(x.items()):
                if hasattr(v,"isoformat"):x[k]=v.isoformat()
                elif not isinstance(v,(str,int,float,bool,type(None))):x[k]=str(v)
            x["observed_closed"]=evidence
            x["after_fee_pnl_verified"]=False
            out.append(x)
        return out
    finally:conn.close()

def mark_reported(rec_id,connect=db_connect):
    if not re.fullmatch(r"TO-20[0-9]{6}-[A-Z0-9.]+-T[1-4]-[A-Z0-9]+",rec_id):
        raise Unsafe("noncanonical recommendation ID")
    conn=connect("PAPER_BRIDGE_AUDIT_CNF")
    try:
        cur=conn.cursor(dictionary=True)
        conn.start_transaction()
        cur.execute("SELECT e.evidence_json,i.source_task FROM "+EVENTS+" e JOIN "+
                    INTENTS+" i ON i.recommendation_id=e.recommendation_id WHERE "+
                    "e.recommendation_id=%s AND e.event_type='BROKER_FILL_READBACK' "+
                    "ORDER BY e.id DESC LIMIT 30",(rec_id,))
        rows=cur.fetchall()
        proof=None;source=None
        for r in rows:
            e=r["evidence_json"]
            if isinstance(e,str):e=json.loads(e)
            if e.get("state")=="CLOSED_NEEDS_FEE_RECON" and e.get("fill_activity_ids"):
                proof=e;source=r["source_task"]
                break
        if not proof:raise Unsafe("no independently matched CLOSED fill activities")
        activity_id=sorted(proof["fill_activity_ids"])[-1]
        cur.execute("INSERT INTO "+WATERMARK+
                    "(recommendation_id,latest_closed_activity_id,source_task) "+
                    "VALUES(%s,%s,%s)",(rec_id,activity_id,source))
        conn.commit()
        return {"recommendation_id":rec_id,"audit_marked":True,
                "closed_activity_reference":activity_id}
    except Exception:
        conn.rollback()
        raise
    finally:conn.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("pending","mark-reported"))
    p.add_argument("--recommendation-id")
    a=p.parse_args()
    if a.mode=="pending":
        print(json.dumps(pending(),sort_keys=True))
    else:
        if not a.recommendation_id:raise Unsafe("recommendation ID required")
        print(json.dumps(mark_reported(a.recommendation_id),sort_keys=True))
if __name__=="__main__":main()
