"""Offline SRM gate, journal and continuation safety; no broker or Pushover I/O."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_monitor as base
m=base.m

class SRMSafety(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,11,19,20,0,tzinfo=dt.timezone.utc)
        self.seed=base.MonitorTests()
        self.seed.setUp()
    def gate(self,root):
        p=Path(root)/"gate.json"
        doc={"schema_version":1,"status_valid":True,"timezone":"America/Chicago",
             "calendar_coverage_ok":True,"calendar_coverage_through":"2026-11-21",
             "calendar_revision":"3300","paused":False,
             "published_at":(self.now-dt.timedelta(seconds=20)).isoformat(),
             "valid_until":(self.now+dt.timedelta(seconds=100)).isoformat(),
             "next_check_at":(self.now+dt.timedelta(days=1)).isoformat()}
        p.write_text(json.dumps(doc));p.chmod(0o600)
        return p,doc
    def test_gate_valid_and_expired_or_stale_or_untrusted_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p,doc=self.gate(tmp)
            with patch.object(m,'GATE',p):
                self.assertEqual(m.authorized_gate(self.now),(True,'GATE_VALID'))
                for key,update in (
                  ('published_at',(self.now-dt.timedelta(seconds=151)).isoformat()),
                  ('valid_until',(self.now-dt.timedelta(seconds=1)).isoformat()),
                  ('next_check_at',(self.now-dt.timedelta(seconds=1)).isoformat()),
                  ('paused',True),
                  ('status_valid',False),
                  ('calendar_revision',""),
                  ('calendar_coverage_through',"2026-11-18"),
                ):
                    d=dict(doc);d[key]=update;p.write_text(json.dumps(d))
                    self.assertFalse(m.authorized_gate(self.now)[0],key)
                p.write_text(json.dumps(doc))
                p.chmod(0o666)
                self.assertFalse(m.authorized_gate(self.now)[0])
                p.chmod(0o600)
                symlink=Path(tmp)/"linked.json";symlink.symlink_to(p)
                with patch.object(m,'GATE',symlink):
                    self.assertFalse(m.authorized_gate(self.now)[0])
    def test_missing_one_verified_scan_breaks_episode_and_creates_new_h1(self):
        state={}
        for minute in range(7):
            scan,now=self.seed.scan_at(minute)
            picks,_=m.decide(scan,now,state)
            if picks:
                state['episodes']['AMD']['last_alerted_hour']=picks[0]['consecutive_hours']
        previous=state['episodes']['AMD']['started_at']
        scan,now=self.seed.scan_at(7,False)
        picks,_=m.decide(scan,now,state)
        self.assertEqual(picks,[])
        self.assertFalse(state['episodes']['AMD']['active'])
        scan,now=self.seed.scan_at(8)
        picks,_=m.decide(scan,now,state)
        self.assertEqual(len(picks),1)
        self.assertEqual(picks[0]['consecutive_hours'],1)
        self.assertNotEqual(previous,state['episodes']['AMD']['started_at'])
        for minute in range(9,62):
            scan,now=self.seed.scan_at(minute)
            picks,_=m.decide(scan,now,state)
            self.assertFalse(any(p['consecutive_hours']==2 for p in picks))
    def test_stale_feed_breaks_episode_even_when_later_scan_newly_valid(self):
        state={}
        for minute in range(3):
            scan,now=self.seed.scan_at(minute)
            picks,_=m.decide(scan,now,state)
            for p in picks:state['episodes'][p['symbol']]['last_alerted_hour']=1
        stale,now=self.seed.scan_at(3)
        stale['asof']=(now-dt.timedelta(minutes=5)).isoformat()
        picks,status=m.decide(stale,now,state)
        self.assertEqual(status,'SCAN_STALE');self.assertEqual(picks,[])
        self.assertFalse(state['episodes']['AMD']['active'])
        fresh,now=self.seed.scan_at(4)
        picks,status=m.decide(fresh,now,state)
        self.assertEqual([x['consecutive_hours'] for x in picks],[1])
    def test_exactly_one_new_episode_hour_record_even_if_order_handoff_blocked(self):
        import watcher_event
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            public=root/"public";public.mkdir()
            scan,now=self.seed.scan_at(0)
            calls=[]
            def blocked(*args,**kw):
                calls.append(1)
                return {'status':'BLOCKED_NEWS','event_id':'MOCK'}
            with patch.object(m,'ROOT',root),patch.object(m,'PUBLIC',public/'latest.json'),\
                 patch.object(m,'authorized_gate',return_value=(True,'GATE_VALID')),\
                 patch.object(m,'latest_scan',return_value=scan),\
                 patch.object(watcher_event,'emit',side_effect=blocked):
                result=m.run(now,notify=True)
                journal=root/('sustained-alerts-'+now.astimezone(m.CT).date().isoformat()+'.jsonl')
                self.assertTrue(journal.exists())
                entries=[json.loads(line) for line in journal.read_text().splitlines()]
                self.assertEqual(len(entries),1)
                self.assertEqual(entries[0]['route_status'],'ROUTE_OUTCOME_UNKNOWN_USE_ORDER_RECEIPTS')
                self.assertEqual(entries[0]['hour'],1)
                self.assertEqual(result['order_handoffs'][0]['status'],'BLOCKED_NEWS')
                self.assertEqual(len(calls),1)
                m.run(now,notify=True)
                self.assertEqual(len(journal.read_text().splitlines()),1)
                self.assertEqual(len(calls),1)
    def test_unknown_route_has_durable_event_without_claiming_broker_fill(self):
        import watcher_event
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);public=root/"public";public.mkdir()
            scan,now=self.seed.scan_at(0)
            with patch.object(m,'ROOT',root),patch.object(m,'PUBLIC',public/'latest.json'),\
                 patch.object(m,'authorized_gate',return_value=(True,'GATE_VALID')),\
                 patch.object(m,'latest_scan',return_value=scan),\
                 patch.object(watcher_event,'emit',side_effect=OSError('unknown')):
                result=m.run(now,notify=True)
                self.assertEqual(result['order_handoffs'][0]['status'],'HANDOFF_UNAVAILABLE')
                journal=list(root.glob('sustained-alerts-*.jsonl'))
                self.assertEqual(len(journal),1)
                row=json.loads(journal[0].read_text().splitlines()[0])
                self.assertNotIn('FILLED',row['route_status'])
    def test_missing_journal_prevents_broker_order_route(self):
        import watcher_event
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);public=root/"public";public.mkdir()
            scan,now=self.seed.scan_at(0)
            with patch.object(m,'ROOT',root),patch.object(m,'PUBLIC',public/'latest.json'),\
                 patch.object(m,'authorized_gate',return_value=(True,'GATE_VALID')),\
                 patch.object(m,'latest_scan',return_value=scan),\
                 patch.object(m,'journal_verified_hour',side_effect=OSError('readonly')),\
                 patch.object(watcher_event,'emit',side_effect=AssertionError('broker route forbidden')):
                result=m.run(now,notify=True)
                self.assertEqual(result['order_handoffs'],[])
                self.assertEqual(len(list(root.glob('sustained-alerts-*.jsonl'))),0)
    def test_price_floor(self):
        scan,now=self.seed.scan_at(0)
        lead=scan['signals']['sustained_riser_research_leads'][0]
        lead['latest_price']=5.00
        self.assertEqual(len(m.observations(scan,now)),1)
        lead['latest_price']=4.99
        self.assertEqual(len(m.observations(scan,now)),0)
        lead['latest_price']=5.00
        lead['latest_quote']={'kind':'SIP_NBBO_MID','bid':4.99,'ask':5.01,'mid':5}
        self.assertEqual(len(m.observations(scan,now)),0)

    def test_same_key_is_deduped_across_midnight_journal_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            at=dt.datetime(2026,11,20,5,59,tzinfo=dt.timezone.utc)
            row=m.observations(*self.seed.scan_at(0))[0]
            row["consecutive_hours"]=1
            row["episode_started_at_utc"]=(at-dt.timedelta(hours=1)).isoformat()
            m.format_alert(row,self.seed.now,{})
            with patch.object(m,'ROOT',Path(tmp)):
                first=m.journal_verified_hour(row,at)
                second=m.journal_verified_hour(row,at+dt.timedelta(minutes=3))
                self.assertTrue(first)
                self.assertFalse(second)
                total=sum(len(f.read_text().splitlines()) for f in Path(tmp).glob('sustained-alerts-*.jsonl'))
                self.assertEqual(total,1)

if __name__=="__main__":unittest.main(verbosity=2)
