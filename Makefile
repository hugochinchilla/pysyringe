test:
	ENVIRONMENT=test uv run pytest

coverage:
	ENVIRONMENT=test bash -c "uv run coverage run -m pytest && uv run coverage xml && uv run coverage html && uv run coverage report"
