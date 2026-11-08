"""Read-only broker account/position/order preflight for Alpaca PAPER.

Never sends POST, PATCH or DELETE. Uses the same systemd LoadCredential
already installed for the independent PAPER executor. Never displays
credentials, account id, balances or PII in logs.
"""
from __future__ import annotations
import json
import sys
from .auto_paper import paper_api

MANAGED={"SOXX","SOXL","SOXS","MUD"}

def main()->int:
    try:
        account=paper_api("GET","/v2/account")
        positions=paper_api("GET","/v2/positions")
        orders=paper_api("GET","/v2/orders?status=open&limit=500")
        clock=paper_api("GET","/v2/clock")
        if (not isinstance(account,dict) or not account.get("id")
            or account.get("status")!="ACTIVE"
            or account.get("trading_blocked") is not False
            or not isinstance(positions,list) or not isinstance(orders,list)
            or len(orders)>=500 or not isinstance(clock,dict)):
            raise ValueError("Read-only paper account verification incomplete")
        managed=[{"symbol":x.get("symbol"),"qty":str(x.get("qty","?"))}
                 for x in positions if isinstance(x,dict)
                 and x.get("symbol") in MANAGED]
        print(json.dumps({
            "paper_account_verified":True,
            "managed_positions":managed,
            "positions_count":len(positions),
            "open_orders_count":len(orders),
            "market_open":clock.get("is_open") is True,
            "orders_placed":0,
            "paper_only":True,
        },sort_keys=True))
        return 0
    except Exception as err:
        print(json.dumps({"paper_account_verified":False,
                          "error_type":type(err).__name__,
                          "orders_placed":0,"paper_only":True}))
        return 2

if __name__=="__main__":
    sys.exit(main())
