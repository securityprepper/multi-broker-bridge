"""Offline tests: official-form provenance does not become a buy authorization."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("gate", str(Path(__file__).resolve().parents[1] / "research" / "v2_form4_insider_purchase_pit_gate_20261111.py"))
gate = importlib.util.module_from_spec(spec)
import sys
sys.modules["gate"] = gate
spec.loader.exec_module(gate)

ACCEPT = "2026-11-10T21:15:10Z"
OBSERVED = "2026-11-10T21:16:10Z"
DECISION = "2026-11-11T14:30:00Z"
ACCESSION = "0001193125-26-455960"


def fixture(code="P",acq="A",direct="D",shares="1000",price="300",title="Common Stock",
            doc="4",cik="0001325702",symbol="ABC",plan="false",role="true",trade_date="2026-11-10",
            extra="",derivative=""):
    return (f"""<?xml version="1.0"?><ownershipDocument>
      <documentType>{doc}</documentType>
      <issuer><issuerCik>{cik}</issuerCik><issuerTradingSymbol>{symbol}</issuerTradingSymbol></issuer>
      <reportingOwner><reportingOwnerRelationship><isDirector>{role}</isDirector><isOfficer>false</isOfficer></reportingOwnerRelationship></reportingOwner>
      <aff10b5One>{plan}</aff10b5One>
      <nonDerivativeTable><nonDerivativeTransaction>
      <securityTitle><value>{title}</value></securityTitle>
      <transactionDate><value>{trade_date}</value></transactionDate>
      <transactionCoding><transactionCode>{code}</transactionCode></transactionCoding>
      <transactionAmounts><transactionShares><value>{shares}</value></transactionShares>
      <transactionPricePerShare><value>{price}</value></transactionPricePerShare>
      <transactionAcquiredDisposedCode><value>{acq}</value></transactionAcquiredDisposedCode></transactionAmounts>
      <ownershipNature><directOrIndirectOwnership><value>{direct}</value></directOrIndirectOwnership></ownershipNature>
      </nonDerivativeTransaction>{extra}</nonDerivativeTable><derivativeTable>{derivative}</derivativeTable>
      </ownershipDocument>""").encode("utf-8")


def scan(xml=None, **kw):
    kw0 = dict(expected_issuer_cik="1325702", accession=ACCESSION, sec_accepted_at=ACCEPT,
              first_observed_at=OBSERVED, decision_at=DECISION, expected_symbol="ABC")
    kw0.update(kw)
    return gate.evaluate_form4(xml or fixture(), **kw0)


class GateTests(unittest.TestCase):
    def test_positive_still_research_only(self):
        r=scan()
        self.assertEqual(r.decision,"RESEARCH_CANDIDATE_ONLY")
        self.assertEqual(r.direct_purchased_usd,"300000")
        self.assertFalse(r.allowed_to_trade)
        self.assertEqual(len(r.content_sha256),64)
    def test_missing_first_seen_is_no_go_even_after_sec_accepted(self):
        r=scan(first_observed_at=None)
        self.assertIn("MISSING_ORIGINAL_FIRST_SEEN",r.reasons)
        self.assertFalse(r.allowed_to_trade)
    def test_first_seen_after_decision_cannot_hindsight_trade(self):
        r=scan(first_observed_at="2026-11-12T22:00:00Z")
        self.assertIn("FIRST_SEEN_OUTSIDE_CAUSAL_WINDOW",r.reasons)
    def test_future_sec_acceptance_is_no_go(self):
        r=scan(sec_accepted_at="2026-11-12T22:00:00Z")
        self.assertIn("INVALID_OR_FUTURE_SEC_ACCEPTANCE",r.reasons)
    def test_lower_bound_on_first_seen_sec_acceptance(self):
        r=scan(first_observed_at="2026-11-09T21:12:00Z")
        self.assertIn("FIRST_SEEN_OUTSIDE_CAUSAL_WINDOW",r.reasons)
    def test_amendment_no_go(self):
        self.assertIn("NOT_ORIGINAL_FORM4",scan(fixture(doc="4/A")).reasons)
    def test_issuer_and_symbol_must_match(self):
        r=scan(fixture(cik="0001325703",symbol="XYZ"))
        self.assertIn("ISSUER_CIK_MISMATCH",r.reasons)
        self.assertIn("ISSUER_SYMBOL_MISMATCH",r.reasons)
    def test_mixed_sale_no_go_even_with_p_buy(self):
        same=fixture().decode()
        same=same.replace("</nonDerivativeTable>", """
        <nonDerivativeTransaction><transactionCoding><transactionCode>S</transactionCode></transactionCoding></nonDerivativeTransaction>
        </nonDerivativeTable>""")
        self.assertIn("SAME_FORM_SALE_MIXED",scan(same.encode()).reasons)
    def test_indirect_and_10b5_plan_no_go(self):
        r=scan(fixture(direct="I",plan="true"))
        self.assertIn("INDIRECT_OWNERSHIP_AMBIGUITY",r.reasons)
        self.assertIn("AFFIRMED_10B5_1_PLAN",r.reasons)
    def test_grant_exercise_derivative_no_go(self):
        self.assertIn("NO_QUALIFIED_LARGE_DIRECT_P_TRANSACTION",scan(fixture(code="M")).reasons)
        mixed=fixture(derivative="<derivativeTransaction/>")
        self.assertIn("DERIVATIVE_TRANSACTION_PRESENT",scan(mixed).reasons)
    def test_missing_or_nonfinite_quantities_no_go(self):
        for s,p in [("NaN","200"),("1000","Inf"),("0","300"),("1000","0")]:
            with self.subTest(s=s,p=p):
                self.assertIn("NO_QUALIFIED_LARGE_DIRECT_P_TRANSACTION",scan(fixture(shares=s,price=p)).reasons)
    def test_min_ticket_exact_decimal(self):
        self.assertEqual(scan(fixture(shares="1000",price="250")).decision,"RESEARCH_CANDIDATE_ONLY")
        self.assertIn("NO_QUALIFIED_LARGE_DIRECT_P_TRANSACTION",scan(fixture(shares="1000",price="249.99")).reasons)
    def test_stale_transaction_date_rejected(self):
        self.assertIn("TRADE_DATE_STALE_OR_UNKNOWN",scan(fixture(trade_date="2026-10-30")).reasons)
    def test_sec_bool_zero_one_flags_work(self):
        x=fixture().replace(b"<isDirector>true</isDirector>",b"<isDirector>1</isDirector>")
        x=x.replace(b"<aff10b5One>false</aff10b5One>",b"<aff10b5One>0</aff10b5One>")
        self.assertEqual(scan(x).decision,"RESEARCH_CANDIDATE_ONLY")
    def test_plan_unknown_fails_closed(self):
        self.assertIn("AFF10B5_1_STATUS_UNVERIFIED",scan(fixture(plan="unknown")).reasons)
    def test_missing_owner_role_no_go(self):
        self.assertIn("NO_CONFIRMED_OFFICER_OR_DIRECTOR",scan(fixture(role="false")).reasons)
    def test_dtd_and_oversize_rejected(self):
        self.assertIn("XML_PROHIBITED_DTD",scan(b"<!DOCTYPE foo><ownershipDocument/>").reasons)
        self.assertIn("XML_INVALID_SIZE",scan(b"x"*260000).reasons)
    def test_not_security_purchase(self):
        self.assertIn("NOT_ELIGIBLE_COMMON_STOCK",scan(fixture(title="Preferred Stock")).reasons)
        self.assertIn("NO_QUALIFIED_LARGE_DIRECT_P_TRANSACTION",scan(fixture(code="S",acq="D")).reasons)
if __name__=="__main__":unittest.main()