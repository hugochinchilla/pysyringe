PYTHON_VERSIONS := 3.11 3.12 3.13 3.14

.PHONY: test
test:
	@$(foreach v,$(PYTHON_VERSIONS), \
		ENVIRONMENT=test uv run --python $(v) pytest || exit $$?; \
	)

.PHONY: coverage
coverage:
	ENVIRONMENT=test bash -c "uv run coverage run -m pytest && uv run coverage xml && uv run coverage html && uv run coverage report"

.PHONY: coverage-all
coverage-all:
	@$(foreach v,$(PYTHON_VERSIONS), \
		ENVIRONMENT=test uv run --python $(v) coverage run --data-file=.coverage.py$(v) -m pytest || exit $$?; \
	)
	uv run --python 3.15 coverage combine .coverage.py3*
	uv run coverage xml
	uv run coverage html
	uv run coverage report -m

.PHONY: docs
docs:
	uv run python docs/build.py
