TARGET ?= dev
.PHONY: setup test app-check check validate deploy refresh publish app-deploy require-profile
setup:
	bash scripts/setup-dev.sh
test:
	uv run --frozen pytest
app-check:
	npm --prefix app run typecheck
	npm --prefix app run lint
	npm --prefix app test
	npm --prefix app run build
check: test app-check
require-profile:
	@test -n "$(PROFILE)" || (echo 'Set PROFILE to an explicitly chosen Databricks CLI profile.' >&2; exit 1)
	@case "$(TARGET)" in dev|lab) ;; *) echo 'TARGET must be dev or lab' >&2; exit 1;; esac
validate: require-profile
	python3 scripts/validate-config.py --target $(TARGET)
	databricks bundle validate --strict --target $(TARGET) --profile "$(PROFILE)"
deploy: validate
	npm --prefix app run build
	databricks bundle deploy --target $(TARGET) --profile "$(PROFILE)"
	python3 scripts/grant-runtime-source.py --profile "$(PROFILE)" --target $(TARGET)
refresh: require-profile
	databricks bundle run nemweb_refresh --target $(TARGET) --profile "$(PROFILE)"
publish: require-profile
	databricks bundle run nemweb_app_serving --target $(TARGET) --profile "$(PROFILE)"
	python3 scripts/grant-sync-source.py --profile "$(PROFILE)" --target $(TARGET)
app-deploy: validate
	npm --prefix app run build
	databricks bundle sync --full --target $(TARGET) --profile "$(PROFILE)"
	databricks bundle run app --target $(TARGET) --profile "$(PROFILE)"

provision: require-profile
	@test -n "$(CATALOG)" -a -n "$(DEPLOYMENT_ID)" || (echo 'Set CATALOG and DEPLOYMENT_ID.' >&2; exit 1)
	python3 scripts/provision-lakebase.py --profile "$(PROFILE)" --catalog "$(CATALOG)" --deployment-id "$(DEPLOYMENT_ID)" --target $(TARGET)
