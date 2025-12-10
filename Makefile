.PHONY: test
test:
	ENVIRONMENT=test uv run --python 3.11 pytest
	ENVIRONMENT=test uv run --python 3.12 pytest
	ENVIRONMENT=test uv run --python 3.13 pytest
	ENVIRONMENT=test uv run --python 3.14 pytest
	ENVIRONMENT=test uv run --python 3.15 pytest

.PHONY: coverage
coverage:
	ENVIRONMENT=test bash -c "uv run coverage run -m pytest && uv run coverage xml && uv run coverage html && uv run coverage report"
