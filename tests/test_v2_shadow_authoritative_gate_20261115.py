"""Offline-only root projection and no-market-poll fail-closed tests."""
import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from research.v2_shadow_authoritative_gate_20261115 import unpaused, verified_gate

NOW = dt.datetime.fromisoformat("2026-11-15T00:30:00-06:00")

def sample():
    return {"schema_version": 1, "status_valid": True, "timezone":"America/Chicago",
            "paused":False, "calendar_revision":"2", "calendar_coverage_ok":True,
            "calendar_coverage_through":"2036-10-25",
            "published_at":"2026-11-15T00:29:00-06:00",
            "valid_until":"2026-11-15T00:31:30-06:00",
            "next_check_at":"2026-11-20T16:07:00-06:00"}

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir=Path(self.temp.name)
        os.chmod(self.dir,0o700)
        self.path=self.dir/'gate.json'
        self.doc=sample()
    def read(self):
        self.path.write_text(json.dumps(self.doc))
        os.chmod(self.path,0o600)
        return unpaused(NOW,self.path)
    def test_valid(self): self.assertTrue(self.read())
    def test_paused(self): self.doc['paused']=True; self.assertFalse(self.read())
    def test_must_have_status_valid(self):
        self.doc['status_valid']=False
        with self.assertRaises(ValueError): self.read()
    def test_legacy_projection_missing_short_ttl(self):
        del self.doc['valid_until']
        with self.assertRaises((ValueError,KeyError)): self.read()
    def test_invalid_revision(self):
        self.doc['calendar_revision']='1'
        with self.assertRaises(ValueError): self.read()
    def test_stale_published(self):
        self.doc['published_at']='2026-11-14T23:00:00-06:00'
        with self.assertRaises(ValueError): self.read()
    def test_expired_ttl(self):
        self.doc['valid_until']='2026-11-15T00:29:30-06:00'
        with self.assertRaises(ValueError): self.read()
    def test_future_published(self):
        self.doc['published_at']='2026-11-15T00:30:10-06:00'
        with self.assertRaises(ValueError): self.read()
    def test_elapsed_boundary(self):
        self.doc['next_check_at']='2026-11-14T16:07:00-06:00'
        with self.assertRaises(ValueError): self.read()
    def test_wrong_timezone(self):
        self.doc['timezone']='UTC'
        with self.assertRaises(ValueError): self.read()
    def test_coverage_expired(self):
        self.doc['calendar_coverage_through']='2026-11-14'
        with self.assertRaises(ValueError): self.read()
    def test_untrusted_path_symlink(self):
        self.read()
        link=self.dir/'link.json';link.symlink_to(self.path)
        with self.assertRaises(OSError): unpaused(NOW,link)
    def test_untrusted_permission(self):
        self.read();os.chmod(self.path,0o666)
        with self.assertRaises(ValueError): unpaused(NOW,self.path)
    def test_untrusted_parent(self):
        self.read();os.chmod(self.dir,0o777)
        with self.assertRaises(ValueError): unpaused(NOW,self.path)
    def test_invalid_json(self):
        self.path.write_text('{');os.chmod(self.path,0o600)
        with self.assertRaises(ValueError): unpaused(NOW,self.path)
    def test_oversized_file(self):
        self.path.write_text(' '*17000);os.chmod(self.path,0o600)
        with self.assertRaises(ValueError): unpaused(NOW,self.path)
    def test_invalid_gate_no_market_fetch(self):
        from research.v2_forward_only_sector_shadow_20261109 import run
        from zoneinfo import ZoneInfo
        scheduled = dt.datetime(2026,11,16,9,35,25,tzinfo=ZoneInfo('America/New_York'))
        def reject(_):
            return unpaused(scheduled,self.path)
        self.doc['published_at']='2026-11-16T08:35:00-06:00'
        self.doc['valid_until']='2026-11-16T08:37:30-06:00'
        self.doc['paused'] = True
        self.path.write_text(json.dumps(self.doc))
        os.chmod(self.path,0o600)
        result=run(now=scheduled,holiday_check=reject,
                   fetch=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('market request despite PAUSE')))
        self.assertEqual(result['market_data_requests'],0)
        self.assertEqual(result['status'],'HOLIDAY_PAUSED_NO_POLL')

    def test_weekend_no_fetch(self):
        from research.v2_forward_only_sector_shadow_20261109 import run
        result=run(now=NOW,holiday_check=lambda _: (_ for _ in ()).throw(AssertionError('unexpected gate poll')),
                   fetch=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('unexpected market call')))
        self.assertEqual(result['market_data_requests'],0)
        self.assertEqual(result['status'],'NOT_SCHEDULED')

if __name__=='__main__': unittest.main()
