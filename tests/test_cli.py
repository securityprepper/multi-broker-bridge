"""CLI safety negative tests; none contact brokers or submit orders."""
import io
import json
import os
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
from multi_broker_bridge import cli
from multi_broker_bridge.models import LimitOrder, OrderRejected

REQ=["--broker","alpaca","--symbol","SPY","--qty","1",
     "--limit","10.00","--client-order-id","SAFE-0001"]

class CLITests(unittest.TestCase):
    def run_command(self,args):
        out=io.StringIO()
        with redirect_stdout(out),redirect_stderr(io.StringIO()):
            status=cli.main(args)
        return status,json.loads(out.getvalue()) if out.getvalue() else None
    def test_preview_does_not_contact_any_broker(self):
        for broker in ("alpaca","ibkr","robinhood"):
            args=REQ.copy()
            args[1]=broker
            with patch.object(cli.BROKERS[broker],"submit") as send:
                status,doc=self.run_command(args)
            self.assertEqual(status,0)
            send.assert_not_called()
            self.assertIsNone(doc["broker_order_id"])
    def test_alpaca_execute_requires_explicit_environment_gate(self):
        args=REQ+["--execute"]
        with patch.dict(os.environ,{"MULTI_BROKER_ALLOW_PAPER":"0"}),patch.object(cli.alpaca,"submit") as send:
            status,_=self.run_command(args)
        self.assertEqual(status,78)
        send.assert_not_called()
    def test_robinhood_cannot_execute_even_with_paper_gate(self):
        args=REQ.copy()
        args[1]="robinhood"
        with patch.dict(os.environ,{"MULTI_BROKER_ALLOW_PAPER":"1"}),patch.object(cli.robinhood,"submit") as send:
            status,_=self.run_command(args+["--execute"])
        self.assertEqual(status,78)
        send.assert_not_called()
    def test_alpaca_readback_does_not_submit(self):
        with patch.object(cli.alpaca,"readback",return_value={"status":"accepted"}),patch.object(cli.alpaca,"submit") as send:
            status,doc=self.run_command(["--broker","alpaca","--readback","SAFE-0001"])
        self.assertEqual(status,0)
        self.assertEqual(doc["status"],"accepted")
        send.assert_not_called()

if __name__=="__main__":unittest.main()
