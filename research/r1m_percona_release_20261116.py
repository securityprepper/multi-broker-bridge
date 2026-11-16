"""Percona-only transactional R1M PAPER persistence.

Separate from legacy direction_paper SQLite used by OWNED/V2. Reject absent
credential, missing schema, unsafe queries; broker writes remain elsewhere.
The table and SQL compatibility layer preserves upstream reservation/commit
semantics without changing execution, quote or protective-order policies.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path

import mysql.connector
from mysql.connector import errorcode

DB_NAME = "securityprepper_r1m_paper"
DB_USER = "sp_r1m_paper"
CREDENTIAL = "r1m_percona_config"
REQUIRED_TABLES = frozenset((
    "signals", "paper_attempts", "notifications", "trend_state",
    "research_observations", "research_episodes", "research_runs",
    "research_audits", "research_recommendations",
    "research_signal_timing", "research_exit_peaks",
    "research_audit_variants", "research_dollar_exit_audit"
))
PRAGMA = re.compile(r"^PRAGMA table_info\((\w+)\)$", re.I)
DDL_PATTERN = re.compile(
    r"^(?:CREATE TABLE IF NOT EXISTS|CREATE INDEX IF NOT EXISTS)\s+(\w+)",
    re.I)
UPSERT = re.compile(r"\bON CONFLICT\([a-z_,\s]+\)\s+DO UPDATE SET\s+", re.I)
EXCLUDED = re.compile(r"\bexcluded\.(\w+)\b", re.I)


class Result:
    def __init__(self, rows):
        self.rows = tuple(rows)
        self.index = 0

    def fetchone(self):
        if self.index >= len(self.rows):
            return None
        item = self.rows[self.index]
        self.index += 1
        return item

    def fetchall(self):
        rest = list(self.rows[self.index:])
        self.index = len(self.rows)
        return rest

    def __iter__(self):
        return iter(self.rows)


class PerconaLedger:
    def __init__(self, connection):
        self.connection = connection
        cur = connection.cursor(buffered=True)
        try:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema=%s", (DB_NAME,))
            tables = {str(row[0]) for row in cur.fetchall()}
            if not REQUIRED_TABLES.issubset(tables):
                raise RuntimeError(
                    "R1M_PERCONA_SCHEMA_INCOMPLETE:" +
                    ",".join(sorted(REQUIRED_TABLES-tables)))
            cur.execute("SHOW COLUMNS FROM paper_attempts")
            cols = {str(row[0]) for row in cur.fetchall()}
            required = {
                "id","signal_id","client_order_id","fill_price","filled_qty",
                "filled_at_utc","entry_signal_price","entry_vs_close_pct",
                "entry_momentum_pct","exit_reason","audit_completed_at_utc"
            }
            if not required.issubset(cols):
                raise RuntimeError("R1M_PERCONA_AUDIT_COLUMNS_INCOMPLETE")
        finally:
            cur.close()

    def execute(self, query, parameters=()):
        if not isinstance(query, str):
            raise TypeError("SQL_QUERY_NOT_TEXT")
        sql = query.strip()
        match = PRAGMA.fullmatch(sql)
        if match:
            table = match.group(1)
            if table not in REQUIRED_TABLES:
                raise ValueError("UNEXPECTED_PRAGMA_TABLE")
            cur = self.connection.cursor(buffered=True)
            try:
                cur.execute("SHOW COLUMNS FROM `" + table + "`")
                return Result([(idx, row[0]) for idx, row in enumerate(cur.fetchall())])
            finally:
                cur.close()
        sql = re.sub(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\b",
                     "INSERT IGNORE INTO", sql, flags=re.I)
        sql = re.sub(r"^\s*INSERT\s+OR\s+REPLACE\s+INTO\b",
                     "REPLACE INTO", sql, flags=re.I)
        if "ON CONFLICT" in sql.upper():
            if not UPSERT.search(sql):
                raise ValueError("UNSUPPORTED_PERCONA_UPSERT")
            sql = UPSERT.sub("ON DUPLICATE KEY UPDATE ", sql)
            sql = EXCLUDED.sub(lambda m: "VALUES(" + m.group(1) + ")",sql)
        if not re.match(r"^(?:SELECT|INSERT|REPLACE|UPDATE|DELETE)\b", sql, re.I):
            raise ValueError("PERCONA_LEDGER_NON_DML_REFUSED")
        if isinstance(parameters, (list, tuple)):
            parameters = tuple(parameters)
        else:
            raise TypeError("PERCONA_PARAMS_NOT_SEQUENCE")
        if sql.count("?") != len(parameters):
            raise ValueError("PERCONA_PARAMETER_MISMATCH")
        sql = sql.replace("?", "%s")
        cur = self.connection.cursor(buffered=True)
        try:
            cur.execute(sql, parameters)
            rows = cur.fetchall() if cur.with_rows else []
            return Result(rows)
        except mysql.connector.IntegrityError as e:
            self.connection.rollback()
            if e.errno == errorcode.ER_DUP_ENTRY:
                raise sqlite3.IntegrityError("R1M_DUPLICATE_RESERVATION") from e
            raise
        except BaseException:
            self.connection.rollback()
            raise
        finally:
            cur.close()

    def executescript(self, sql):
        """Verify existing admin-provisioned schema; never run DDL in executor."""
        chunks = [x.strip() for x in sql.split(";") if x.strip()]
        for statement in chunks:
            match = DDL_PATTERN.match(statement)
            if not match:
                raise ValueError("PERCONA_SCHEMA_DDL_CHANGE_REQUIRES_ADMIN")
            if statement.upper().startswith("CREATE TABLE") and match.group(1) not in REQUIRED_TABLES:
                raise ValueError("UNKNOWN_PERCONA_SCHEMA_TABLE")
        return self

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def connect():
    directory = os.getenv("CREDENTIALS_DIRECTORY")
    if not directory:
        raise RuntimeError("R1M_PERCONA_CREDENTIAL_UNAVAILABLE")
    credential = Path(directory)/CREDENTIAL
    if credential.is_symlink() or not credential.is_file():
        raise RuntimeError("R1M_PERCONA_CREDENTIAL_UNAVAILABLE")
    cfg = json.loads(credential.read_text())
    if (set(cfg) != {"user","password","database","unix_socket"}
        or cfg.get("user") != DB_USER or cfg.get("database") != DB_NAME
        or cfg.get("unix_socket") not in
           ("/var/run/mysqld/mysqld.sock","/run/mysqld/mysqld.sock")
        or not isinstance(cfg.get("password"),str)
        or len(cfg["password"])<30):
        raise RuntimeError("R1M_PERCONA_WRONG_CONNECTION_SCOPE")
    con = mysql.connector.connect(**cfg, autocommit=False,
                                  connection_timeout=5)
    try:
        return PerconaLedger(con)
    except BaseException:
        con.close()
        raise
