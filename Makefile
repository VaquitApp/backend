.PHONY: all install format lint test test-postgres run

all: format lint test

install:
	poetry install

format:
	poetry run black src

lint:
	poetry run flake8 src

test:
	rm test.db 2> /dev/null || true
	DB_NAME="./test.db" poetry run pytest -svv .

CONTAINER_NAME="postgres_test_db"

test-postgres:
	docker run --rm --name $(CONTAINER_NAME) -e POSTGRES_DB=postgres \
		-e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
		-d -p 5432:5432 postgres
	sleep 5 # wait for postgres to start
	DB_NAME="postgres" DB_USER="postgres" DB_PASS="postgres" DB_HOST="localhost" DB_PORT="5432" \
		poetry run pytest -svv . || true
	docker stop $(CONTAINER_NAME)

run: install
	poetry run uvicorn src.main:app --host localhost --port 8000 --reload
