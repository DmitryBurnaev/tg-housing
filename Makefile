
lint:
	@echo Linting...
	poetry run ruff check
	poetry run mypy .

format:
	@echo Formatting...
	poetry run ruff format

upgrade:
	@echo Updating dependencies...
	poetry update

migrations-create:
	@read -p "Revision: " db_revision; \
	poetry run alembic revision --autogenerate -m "$$db_revision"

migrations-upgrade:
	@echo Migrations: apply revisions...
	poetry run alembic upgrade head

migrations-downgrade:
	@echo Migrations: downgrade last revisions...
	poetry run alembic downgrade -1

run:
	@echo Run project...
	PYTHONPATH=. poetry run python src/main.py

test:
	@echo Test project...
	PYTHONPATH=. poetry run pytest src/tests

docker-run:
	@echo Run project in docker...
	docker compose up --build bot

docker-test:
	@echo Test project in docker...
	docker compose up --build test

locale-init:
	@echo Localization: init...
	xgettext -o src/i18n/messages.pot src/handlers/*.py
	msginit -i src/i18n/messages.pot -o src/i18n/ru/LC_MESSAGES/messages.po -l ru_RU.UTF-8 --no-translator

locale-update:
	@echo Localization: update tokens...
	xgettext -o src/i18n/messages.pot src/handlers/*.py
	msgmerge --update src/i18n/ru/LC_MESSAGES/messages.po src/i18n/messages.pot

locale-compile:
	@echo Localization: complie translations...
	msgfmt -o src/i18n/ru/LC_MESSAGES/messages.mo src/i18n/ru/LC_MESSAGES/messages.po
