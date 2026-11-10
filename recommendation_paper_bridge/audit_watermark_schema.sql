-- Durable exactly-once notification marker for Task - Recommendation Audit.
CREATE TABLE IF NOT EXISTS securityprepper_trading.sp_paper_rec_audit_watermarks (
 recommendation_id VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
 latest_closed_activity_id VARCHAR(160) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 reported_at_utc DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 source_task VARCHAR(64) NOT NULL,
 CONSTRAINT fk_paper_rec_audit_marker FOREIGN KEY (recommendation_id)
 REFERENCES securityprepper_trading.sp_paper_rec_intents(recommendation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
