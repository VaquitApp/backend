all: format lint test

install:
	poetry install

format:
	poetry run black src

lint:
	poetry run flake8 src

test:
	rm test.db 2> /dev/null || true
	DB_NAME="./test.db" poetry run pytest -sv .

run: install
	poetry run uvicorn src.main:app --host localhost --port 8000 --reload
