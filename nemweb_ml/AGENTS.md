# NEMWEB ML starter guidance

Use only attributed historical data and chronological splits. Reject feature
rows newer than their prediction time or label. The checked-in fixture proves
contracts, not model usefulness. Training and scoring run as serverless
Databricks jobs, not in an assistant's local process. Set the Unity Catalog
registry URI to `databricks-uc`; a real eligible run may set `@challenger` only.
Never change `@prod` or add Model Serving without a separate decision.
