PYTHON ?= python3
PROFILE ?=

.PHONY: setup test foundation-test foundation-snapshot modern-apis build app-install app-typegen app-test app-dev-mock ticket-verify ml-test lakebase-test bundle-validate bundle-validate-live-evidence facilitator-lakebase-preflight facilitator-lakebase-smoke validate-fast validate-local validate-readonly

setup:
	bash scripts/setup-dev.sh

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
	cd nemweb_app && npm run typegen && npm run typecheck && npm run lint && npm run lint:ast-grep && npm run test -- --run && npm run build && npm run smoke:install && npm run test:smoke

app-dev-mock:
	cd nemweb_app && VITE_DATA_MODE=mock npx vite --config client/vite.config.ts --host 127.0.0.1

ticket-verify:
	@test -n "$(ISSUE)" || (echo 'ISSUE=<number> is required' >&2; exit 2)
	$(MAKE) test app-test ml-test lakebase-test

ml-test:
	uv run --project nemweb_ml --extra test $(PYTHON) -m pytest nemweb_ml/tests -q

lakebase-test:
	uv run --extra test $(PYTHON) -m pytest workshop/lakebase/tests -q

# Targets carry their own defaults. No .env.
bundle-validate:
	@test -n "$(PROFILE)" || (echo 'PROFILE=<name> is required' >&2; exit 2)
	(cd nemweb_foundation && databricks bundle validate --strict -t dev --profile $(PROFILE))
	(cd nemweb_ml && databricks bundle validate --strict -t dev --profile $(PROFILE))

bundle-validate-live-evidence:
	@test -n "$(PROFILE)" || (echo 'PROFILE=<name> is required' >&2; exit 2)
	(cd nemweb_foundation && databricks bundle validate --strict -t live_evidence --profile $(PROFILE))

# Fast, workspace-free checks for normal development. The full local gate below
# remains available before a handoff or workshop rehearsal.
validate-fast: test foundation-snapshot modern-apis

validate-local: validate-fast build app-test

facilitator-lakebase-preflight:
	@test -n "$(PROFILE)" || (echo 'PROFILE=<name> is required' >&2; exit 2)
	PROFILE=$(PROFILE) bash workshop/lakebase/scripts/discover.sh

facilitator-lakebase-smoke:
	@test -n "$(PROFILE)" || (echo 'PROFILE=<name> is required' >&2; exit 2)
	uv run --extra test $(PYTHON) -m pytest workshop/lakebase/tests -q

validate-readonly:
	@test -n "$(PROFILE)" || (echo 'PROFILE=<name> is required' >&2; exit 2)
	$(MAKE) validate-local
	$(MAKE) bundle-validate PROFILE=$(PROFILE)
	cd nemweb_app && databricks apps validate --profile $(PROFILE)
