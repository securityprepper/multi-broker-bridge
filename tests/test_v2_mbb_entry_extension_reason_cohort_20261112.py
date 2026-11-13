"""Offline deterministic tests; no live data or network needed."""
import importlib.util
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "research" / "v2_mbb_entry_extension_reason_cohort_20261112.py"
spec = importlib.util.spec_from_file_location("extension_cohort", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def record(watch, skipped, orders=()):
    return {"status":"SCAN_COMPLETE","buy_watch_symbols":watch,
            "skipped_buy_reasons":[{"symbol":s,"reason":r} for s,r in skipped],
            "orders":[{"symbol":s,"status":"pending_new"} for s in orders]}

def test_repeated_scan_appearances_not_independent_trades():
    row=record(["AMD","MU"],[("AMD","ENTRY_EXTENSION_BLOCKED_+2.50%_CAP_2.0%"),
                               ("MU","PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY")])
    x=mod.study([row,row])
    assert x["counts"]["completed_scans"]==2
    assert x["counts"]["extension_appearances"]==2
    assert x["counts"]["extension_unique_symbols"]==1

def test_caps_only_rejected_subset():
    row=record(["AMD","MU","NVDA"],[("AMD","ENTRY_EXTENSION_BLOCKED_+2.01%_CAP_2.0%"),
       ("MU","ENTRY_EXTENSION_BLOCKED_+4.33%_CAP_2.0%")],orders=["NVDA"])
    x=mod.study([row])
    assert x["extension_rejection_only_cap_sensitivity"]["2"]["rejected_appearances_at_or_below_cap"]==0
    assert x["extension_rejection_only_cap_sensitivity"]["2.5"]["rejected_appearances_at_or_below_cap"]==1
    assert x["extension_rejection_only_cap_sensitivity"]["5"]["rejected_appearances_at_or_below_cap"]==2
    assert x["counts"]["order_reply_records_NOT_FILLS"]==1

def test_invalid_extension_and_unrelated_skips_do_not_count_as_extension():
    row=record(["AMD","MU"],[("AMD","NO_FRESH_BID_ASK"),
       ("MU","ENTRY_EXTENSION_BLOCKED_+NaN%_CAP_2.0%")])
    x=mod.study([row])
    assert x["counts"]["extension_appearances"]==0
    assert x["other_reasons"]["NO_FRESH_BID_ASK"]==1

def test_non_scan_and_invalid_json_are_not_counted():
    data=['not json', '{"status":"FAIL_CLOSED"}',
      '{"MESSAGE":"{\\"status\\":\\"SCAN_COMPLETE\\",\\"buy_watch_symbols\\":[\\"OXY\\"],\\"skipped_buy_reasons\\":[],\\"orders\\":[]}"}']
    x=mod.study(mod.messages(data))
    assert x["counts"]["completed_scans"]==1
    assert x["counts"]["json_status_FAIL_CLOSED"]==1

def test_below_cap_reasons_fail_closed():
    row=record(["AMD"],[("AMD","ENTRY_EXTENSION_BLOCKED_+1.25%_CAP_2.0%")])
    x=mod.study([row])
    assert x["counts"]["bad_extension_reason"]==1
    assert x["counts"]["extension_appearances"]==0
