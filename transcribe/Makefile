.PHONY: install run test cov

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest tests/

cov:
	pytest --cov=app tests/
