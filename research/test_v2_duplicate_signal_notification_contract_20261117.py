"""R1M/V2 independent research regression: duplicate handoff must be no-op, not crash.

No network, broker POST, credentials, or production ledger writes.
Run only in isolated research environments with direction_paper importable.
"""
from __future__ import annotations
import datetime as dt
import importlib.util
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
import direction_paper as production_module

OLD = "return {'signal':signal['id'],'status':'ALREADY_HANDLED','order_attempts':0}"
NEW = "return {'signal':signal['id'],'status':'ALREADY_HANDLED','order_attempts':0,'notification':'NO_POST_NO_TRADING_ALERT'}"

def verify():
    now=dt.datetime.now(dt.timezone.utc)
    with tempfile.TemporaryDirectory(prefix="v2_duplicate_no_broker_") as directory:
        path=Path(directory)/"shadow.sqlite3"
        db=production_module.connect(path)
        signal=production_module.make_signal("V2","replayed-event","AMD","UP",
                "EARLY_REBOUND",now)
        assert production_module.save_signal(db,signal,now) is True
        db.close()
        def no_broker(*args, **kwargs):
            raise AssertionError("ANY_BROKER_ACCESS_PROHIBITED")
        def reader(_now,_cutoff):
            return [signal],[]
        with patch.object(production_module,"trusted_gate",return_value=False):
            try:
                production_module.run(now=now,execute=False,state=path,
                       reader=reader,broker=no_broker,quotes=no_broker)
            except KeyError as exc:
                assert exc.args == ("notification",)
            else:
                raise AssertionError("ORIGINAL_DUPLICATE_FAILURE_NOT_REPRODUCED")
        contents=Path(production_module.__file__).read_text()
        assert contents.count(OLD)==1
        patched_file=Path(directory)/"patched_module.py"
        patched_file.write_text(contents.replace(OLD,NEW))
        spec=importlib.util.spec_from_file_location("isolated_v2_duplicate_fix",patched_file)
        isolated=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(isolated)
        with patch.object(isolated,"trusted_gate",return_value=False):
            result=isolated.run(now=now,execute=False,state=path,
                         reader=reader,broker=no_broker,quotes=no_broker)
        assert result["status"]=="SHADOW_ONLY"
        assert result["order_attempts"]==0 and result["notifications"]==0
        assert result["processed"][0]["status"]=="ALREADY_HANDLED"
        assert result["processed"][0]["notification"]=="NO_POST_NO_TRADING_ALERT"
        check=sqlite3.connect(path)
        try:
            assert check.execute("SELECT COUNT(*) FROM signals").fetchone()[0]==1
            assert check.execute("SELECT COUNT(*) FROM paper_attempts").fetchone()[0]==0
        finally:
            check.close()
    return "RESEARCH_DUPLICATE_RETURN_PATCH_PASS_NO_BROKER_CALLS"

if __name__=="__main__":
    print(verify())
