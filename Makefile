test:
	ENVIRONMENT=test pytest

coverage:
	ENVIRONMENT=test bash -c "coverage run -m pytest && coverage xml && coverage html && coverage report"
