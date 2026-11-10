-- Isolated idempotent emergency/mandatory PAPER flatten reservations.
-- Never alter or delete V1 broker ledger, orders, or monitor data.
CREATE TABLE IF NOT EXISTS securityprepper_trading.sp_paper_rec_flatten_intents (
 recommendation_id VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
 client_order_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 quantity DECIMAL(14,6) NOT NULL,
 status VARCHAR(44) NOT NULL,
 paper_broker_order_id VARCHAR(80) DEFAULT NULL,
 reserved_at_utc DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 checked_at_utc DATETIME(6) DEFAULT NULL,
 evidence_json JSON DEFAULT NULL,
 UNIQUE KEY uq_paper_flatten_client (client_order_id),
 CONSTRAINT fk_paper_rec_flatten FOREIGN KEY (recommendation_id)
 REFERENCES securityprepper_trading.sp_paper_rec_intents(recommendation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
