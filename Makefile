all: format lint test

install:
	poetry install

format:
	poetry run black src

lint:
	poetry run flake8 src

clean-db:
	rm sql_app.db 2> /dev/null || true

test: clean-db
	poetry run pytest -sv .

run: install
	poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --lifespan on
