.PHONY: lint format type-check test check run dashboard clean

lint:
	ruff check job_monitor/ tests/

format:
	ruff format job_monitor/ tests/

type-check:
	mypy job_monitor/

test:
	pytest --cov=job_monitor --cov-report=term-missing -q

check: lint type-check test

run:
	python runner.py

dashboard:
	streamlit run job_monitor/dashboard/app.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; find . -name "*.pyc" -delete 2>/dev/null; true
