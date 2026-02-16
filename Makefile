VENV ?= .venv
PYTHON ?= python3
PIP ?= pip3

ifneq ("$(wildcard $(VENV)/bin/python)","")
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
endif

.PHONY: help install migrate makemigrations createsuperuser collectstatic check run runserver shell test clean lint format reset-db setup docker-build docker-run docker-shell

help:
	@echo "Calendar API commands:"
	@echo "  make install          Install dependencies from requirements.txt"
	@echo "  make makemigrations   Create Django migrations"
	@echo "  make migrate          Apply Django migrations"
	@echo "  make createsuperuser  Create a superuser account"
	@echo "  make collectstatic    Collect static files"
	@echo "  make check            Run Django system checks"
	@echo "  make run              Alias for runserver"
	@echo "  make runserver        Start dev server on 0.0.0.0:8000"
	@echo "  make shell            Open Django shell"
	@echo "  make test             Run test suite"
	@echo "  make clean            Remove local cache artifacts"
	@echo "  make lint             Run flake8 (if installed)"
	@echo "  make format           Run black (if installed)"
	@echo "  make reset-db         Reset local sqlite DB and regenerate migrations"
	@echo "  make setup            Install and migrate"
	@echo "  make docker-build     Build local Docker image"
	@echo "  make docker-run       Run local Docker image on :8000"
	@echo "  make docker-shell     Open shell in local Docker image"

install:
	$(PIP) install -r requirements.txt

makemigrations:
	$(PYTHON) manage.py makemigrations

migrate:
	$(PYTHON) manage.py migrate

createsuperuser:
	$(PYTHON) manage.py createsuperuser

collectstatic:
	$(PYTHON) manage.py collectstatic --noinput

check:
	$(PYTHON) manage.py check

run: runserver

runserver:
	DEBUG=True $(PYTHON) manage.py runserver 0.0.0.0:8000

shell:
	$(PYTHON) manage.py shell

test:
	$(PYTHON) manage.py test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".DS_Store" -delete

lint:
	@echo "Running flake8..."
	@$(PYTHON) -m flake8 . --exclude=migrations,venv,.venv || echo "flake8 not installed in current Python env."

format:
	@echo "Formatting code with black..."
	@$(PYTHON) -m black . || echo "black not installed in current Python env."

reset-db:
	@echo "Resetting database..."
	rm -f db.sqlite3
	find calendar_api/migrations -name "*.py" ! -name "__init__.py" -delete
	$(PYTHON) manage.py makemigrations
	$(PYTHON) manage.py migrate
	@echo "Database reset complete."

setup: install migrate
	@echo "Setup complete."
	@echo "Run 'make createsuperuser' to create an admin account."
	@echo "Run 'make runserver' to start the development server."

docker-build:
	docker build -t calendar-api:dev .

docker-run:
	docker run --rm -it -p 8000:8000 --env-file .env calendar-api:dev

docker-shell:
	docker run --rm -it --entrypoint sh calendar-api:dev
