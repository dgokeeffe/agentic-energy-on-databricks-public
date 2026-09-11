-- Run with psql --set=app_principal=<app service_principal_client_id> after sync creation.
-- app_read is sync-owned; app_write is created and owned by the deployed app.
GRANT USAGE ON SCHEMA app_read TO :"app_principal";
GRANT SELECT ON app_read.nem_region_status_synced,
  app_read.nem_fuel_generation_synced,
  app_read.nem_unit_dispatch_synced TO :"app_principal";
