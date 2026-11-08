"""Capabilities must never imply live or Robinhood PAPER execution."""
import io
import json
import unittest
from contextlib import redirect_stdout
from multi_broker_bridge.capabilities import CAPABILITIES
from multi_broker_bridge.cli import main

class CapabilityTests(unittest.TestCase):
    def test_no_live_capabilities(self):
        self.assertEqual(set(CAPABILITIES),{"alpaca","ibkr","webull","robinhood"})
        for broker,info in CAPABILITIES.items():
            self.assertFalse(info["live_enabled"])
            self.assertFalse(info["operationally_verified"])
        self.assertFalse(CAPABILITIES["robinhood"]["paper_environment"])
        self.assertEqual(CAPABILITIES["robinhood"]["order_types"],[])
        for broker in ("alpaca","ibkr","webull"):
            self.assertTrue(CAPABILITIES[broker]["paper_environment"])
            self.assertEqual(CAPABILITIES[broker]["order_types"],["limit"])
            self.assertFalse(CAPABILITIES[broker]["extended_hours"])
    def test_capabilities_do_not_contact_broker(self):
        for broker in CAPABILITIES:
            output=io.StringIO()
            with redirect_stdout(output):
                status=main(["--broker",broker,"--capabilities"])
            self.assertEqual(status,0)
            info=json.loads(output.getvalue())
            self.assertEqual(info["broker"],broker)
            self.assertFalse(info["operationally_verified"])

if __name__=="__main__":
    unittest.main()
