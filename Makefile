PYTHON ?= python3
PROFILE ?= DEFAULT

.PHONY: setup miniwiki test foundation-test foundation-snapshot modern-apis build app-install app-typegen app-test app-dev-mock ticket-verify ml-test lakebase-test links safety bundle-validate bundle-validate-live-evidence facilitator-lakebase-preflight facilitator-lakebase-smoke validate-local validate-readonly

setup:
	bash scripts/setup-dev.sh

miniwiki:
	$(PYTHON) scripts/validate-miniwiki.py

links:
	$(PYTHON) scripts/validate-markdown-links.py

safety:
	uv run --extra test $(PYTHON) scripts/validate-repository-safety.py

test:
	uv run --extra test $(PYTHON) -m pytest

foundation-test:
	uv run --project nemweb_foundation --extra test $(PYTHON) -m pytest

foundation-snapshot:
	uv run --project nemweb_foundation $(PYTHON) nemweb_foundation/scripts/validate_nemweb_snapshot.py

modern-apis:
	$(PYTHON) nemweb_foundation/scripts/check_modern_pipeline_apis.py

build:
	rm -rf dist nemweb_foundation/dist nemweb_ml/dist
	uv build --wheel --out-dir dist
	uv build --project nemweb_foundation --wheel --out-dir nemweb_foundation/dist
	uv build --project nemweb_ml --wheel --out-dir nemweb_ml/dist

app-install:
	cd nemweb_app && npm ci --include=dev

app-typegen:
	cd nemweb_app && npm run typegen

app-test:
	cd nemweb_app && npm ci --include=dev && npm run typegen && npm run typecheck && npm run lint && npm run lint:ast-grep && npm run test -- --run && npm run build && npm run smoke:install && npm run test:smoke

app-dev-mock:
	cd nemweb_app && VITE_DATA_MODE=mock npx vite --config client/vite.config.ts --host 127.0.0.1

ticket-verify:
	@test -n "$(ISSUE)" || (echo 'ISSUE=<number> is required' >&2; exit 2)
	$(MAKE) test app-test ml-test lakebase-test

ml-test:
	uv run --project nemweb_ml --extra test $(PYTHON) -m pytest nemweb_ml/tests -q

lakebase-test:
	uv run --extra test $(PYTHON) -m pytest workshop/lakebase/tests -q

# Eight bundle variables have no default and no value is committed, so this
# target sources the operator's local .env (see env.example). Without it the
# first required variable fails validation before the bundle is reached.
bundle-validate:
	@test "$(PROFILE)" = "DEFAULT" || (echo 'PROFILE=DEFAULT is required' >&2; exit 2)
	@test -f .env || (echo 'Missing .env. Copy env.example to .env and set every BUNDLE_VAR_ value.' >&2; exit 2)
	set -a; . ./.env; set +a; \
	  for v in resource_prefix catalog schema app_serving_schema landing_volume warehouse_id participant_group facilitator_group \
	           mlflow_experiment_name uc_model_name training_table feature_table prediction_table; do \
	    eval "val=\$$BUNDLE_VAR_$$v"; \
	    test -n "$$val" || { echo "Missing BUNDLE_VAR_$$v in .env (required, no default)" >&2; exit 2; }; \
	  done; \
	  (cd nemweb_foundation && databricks bundle validate --strict -t dev --profile $(PROFILE)) && \
	  (cd nemweb_ml && databricks bundle validate --strict -t dev --profile $(PROFILE))

bundle-validate-live-evidence:
	@test "$(PROFILE)" = "DEFAULT" || (echo 'PROFILE=DEFAULT is required' >&2; exit 2)
	@test -f .env || (echo 'Missing .env' >&2; exit 2)
	set -a; . ./.env; set +a; \
	  for v in resource_prefix schema landing_schema landing_volume app_serving_schema; do \
	    eval "live=\$$BUNDLE_VAR_live_evidence_$$v"; \
	    eval "dev=\$$BUNDLE_VAR_$$v"; \
	    test -n "$$live" && test "$$live" != "$$dev" || exit 2; \
	  done; \
	  (cd nemweb_foundation && databricks bundle validate --strict -t live_evidence --profile $(PROFILE))

validate-local: miniwiki links safety test foundation-snapshot modern-apis build app-test

facilitator-lakebase-preflight:
	@test "$(PROFILE)" = "DEFAULT" || (echo 'PROFILE=DEFAULT is required' >&2; exit 2)
	PROFILE=$(PROFILE) bash workshop/lakebase/scripts/discover.sh

facilitator-lakebase-smoke:
	@test "$(PROFILE)" = "DEFAULT" || (echo 'PROFILE=DEFAULT is required' >&2; exit 2)
	uv run --extra test $(PYTHON) -m pytest workshop/lakebase/tests -q

validate-readonly: validate-local
	@test "$(PROFILE)" = "DEFAULT" || (echo 'PROFILE=DEFAULT is required' >&2; exit 2)
	$(MAKE) bundle-validate PROFILE=$(PROFILE)
	cd nemweb_app && databricks apps validate --profile $(PROFILE)
