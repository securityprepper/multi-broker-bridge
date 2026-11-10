-- V2 recommendation-to-Alpaca PAPER bridge. New tables only; no V1 schema mutation.
CREATE TABLE IF NOT EXISTS securityprepper_trading.sp_paper_rec_intents (
 recommendation_id VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 created_at_utc DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 issued_at_utc DATETIME(6) NOT NULL,
 quote_at_utc DATETIME(6) NOT NULL,
 expires_at_utc DATETIME(6) NOT NULL,
 session_date DATE NOT NULL,
 symbol VARCHAR(12) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 action VARCHAR(24) NOT NULL,
 source_task VARCHAR(64) NOT NULL,
 source_run_id VARCHAR(128) NOT NULL,
 rationale TEXT NOT NULL,
 quote_last DECIMAL(18,6) NOT NULL,
 quote_bid DECIMAL(18,6) NOT NULL,
 quote_ask DECIMAL(18,6) NOT NULL,
 limit_price DECIMAL(18,6) NOT NULL,
 profit_target DECIMAL(18,6) NOT NULL,
 stop_loss DECIMAL(18,6) NOT NULL,
 intended_qty INT UNSIGNED NOT NULL,
 client_order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 status VARCHAR(44) NOT NULL DEFAULT 'PENDING',
 broker_order_id VARCHAR(80) DEFAULT NULL,
 broker_status VARCHAR(48) DEFAULT NULL,
 failure_code VARCHAR(120) DEFAULT NULL,
 paper_account_fingerprint VARCHAR(64) DEFAULT NULL,
 broker_receipt_json JSON DEFAULT NULL,
 last_checked_utc DATETIME(6) DEFAULT NULL,
 updated_at_utc DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
 UNIQUE KEY uq_client_order_id (client_order_id),
 INDEX ix_paper_rec_status (status, issued_at_utc)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE TABLE IF NOT EXISTS securityprepper_trading.sp_paper_rec_events (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
 recommendation_id VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 observed_at_utc DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 event_type VARCHAR(56) NOT NULL,
 evidence_json JSON NOT NULL,
 INDEX ix_paper_rec_event (recommendation_id,id),
 CONSTRAINT fk_paper_rec_event FOREIGN KEY(recommendation_id)
 REFERENCES securityprepper_trading.sp_paper_rec_intents(recommendation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE TABLE IF NOT EXISTS securityprepper_trading.sp_paper_rec_symbol_claims (
 session_date DATE NOT NULL,
 paper_account_fingerprint VARCHAR(64) NOT NULL,
 symbol VARCHAR(12) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 recommendation_id VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 claimed_at_utc DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 PRIMARY KEY(session_date,paper_account_fingerprint,symbol),
 UNIQUE KEY uq_paper_rec_claim (recommendation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
