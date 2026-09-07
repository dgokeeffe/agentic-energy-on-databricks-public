-- Idempotent batch target contract. Render IDENTIFIER parameters in the job.
CREATE TABLE IF NOT EXISTS IDENTIFIER(:prediction_table) (
  region_id STRING NOT NULL,
  prediction_time TIMESTAMP NOT NULL,
  prediction_score DOUBLE,
  prediction_model_version STRING NOT NULL,
  prediction_feature_time TIMESTAMP NOT NULL,
  prediction_scored_at TIMESTAMP NOT NULL,
  prediction_source_freshness STRING NOT NULL,
  prediction_missing_feature_status STRING NOT NULL
)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true', 'delta.enableRowTracking' = 'true');

-- The scoring job MERGEs on (region_id, prediction_time), overwriting the same
-- challenger version output rather than appending duplicate keys.
