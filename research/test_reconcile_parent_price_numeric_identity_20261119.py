"""Research-only price identity regression for Alpaca PAPER recommendation reconciliation.

No external API, broker POST, DB write, service restart, or credentials are used.
"""
import importlib.util
import math
import pathlib
import unittest
from decimal import Decimal

from recommendation_paper_bridge import reconcile as production
from recommendation_paper_bridge.bridge import Unsafe

STAGED=pathlib.Path("/tmp/v2-recommendation-reconcile-price-research-20261119/reconcile.py")
spec=importlib.util.spec_from_file_location("recommendation_paper_bridge.reconcile_research",STAGED)
staged=importlib.util.module_from_spec(spec)
spec.loader.exec_module(staged)

class PriceIdentityTests(unittest.TestCase):
    def pair(self,ledger_price,broker_price):
        row={"broker_order_id":"BROKER-ORDER-UUID",
             "client_order_id":"QW1-P-CLIENT-ORDER-UUID",
             "symbol":"TEST", "limit_price":ledger_price}
        parent={"id":"BROKER-ORDER-UUID",
                "client_order_id":"QW1-P-CLIENT-ORDER-UUID",
                "symbol":"TEST","side":"buy",
                "order_class":"bracket", "type":"limit",
                "limit_price":broker_price}
        return row,parent

    def test_broker_decimal_display_is_same_price_as_percona_fixed_scale(self):
        for db,api in (("66.130000","66.13"),("435.610000","435.61"),
                       ("5.000000","5.00"),("100.000000","100"),
                       ("0.010000","0.01")):
            with self.subTest(db=db,api=api):
                row,parent=self.pair(Decimal(db),api)
                self.assertIsNone(staged.check_parent(row,parent))

    def test_baseline_rejects_equivalent_numeric_price(self):
        row,parent=self.pair(Decimal("66.130000"),"66.13")
        with self.assertRaises(Unsafe):
            production.check_parent(row,parent)
        self.assertIsNone(staged.check_parent(row,parent))

    def test_price_difference_is_never_rounded_or_tolerated(self):
        for db,api in (("66.130000","66.14"),("66.130000","66.129999"),
                       ("435.610000","435.611"),("5.000000","4.999999")):
            with self.subTest(db=db,api=api):
                row,parent=self.pair(Decimal(db),api)
                with self.assertRaises(Unsafe):
                    staged.check_parent(row,parent)

    def test_missing_zero_nonfinite_and_negative_are_fail_closed(self):
        for bad in (None,"",0,"0","-1","NaN","Infinity","-Infinity",float("nan"),float("inf")):
            with self.subTest(bad=str(bad)):
                row,parent=self.pair(Decimal("66.130000"),bad)
                with self.assertRaises(Unsafe):
                    staged.check_parent(row,parent)
        for bad in ("NaN","Infinity","-Infinity","-1","0",None):
            with self.subTest(db_bad=str(bad)):
                row,parent=self.pair(bad,"66.13")
                with self.assertRaises(Unsafe):
                    staged.check_parent(row,parent)

    def test_order_identity_and_bracket_guards_unchanged(self):
        for key,bad in (("id","WRONG"),("client_order_id","WRONG"),
                        ("symbol","DIFFERENT"),("side","sell"),
                        ("order_class","simple"),("type","market")):
            with self.subTest(key=key):
                row,parent=self.pair(Decimal("66.130000"),"66.13")
                parent[key]=bad
                with self.assertRaises(Unsafe):
                    staged.check_parent(row,parent)

if __name__=="__main__":
    unittest.main(verbosity=2)
