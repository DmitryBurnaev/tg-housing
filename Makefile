.DEFAULT_GOAL := help

.PHONY: help
help: ## This help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*? / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: lint
lint: ## Linting project
	@echo Linting...
	poetry run ruff check
	poetry run mypy .

.PHONY: format
format: ## Apply formatting using black
	@echo Formatting...
	poetry run black .
	poetry run ruff check --fix

.PHONY: upgrade
upgrade: ## Update dependencies
	@echo Updating dependencies...
	poetry update

.PHONY: migrations-create
migrations-create: ## Make migrations
	@read -p "Revision: " db_revision; \
	poetry run alembic revision --autogenerate -m "$$db_revision"

.PHONY: migrations-upgrade
migrations-upgrade: ## Apply migrations
	@echo Migrations: apply revisions...
	poetry run alembic upgrade head

.PHONY: migrate
migrate: ## Apply migrations
	@echo Migrations: apply revisions...
	poetry run alembic upgrade head

.PHONY: migrations-downgrade
migrations-downgrade: ## Downgrade (unapply) migration (last revision)
	@echo Migrations: downgrade last revisions...
	poetry run alembic downgrade -1

.PHONY: run
run: ## Run bot
	@echo Run project...
	PYTHONPATH=. poetry run python src/main.py

.PHONY: test
test: ## Run tests
	@echo Test project...
	PYTHONPATH=. poetry run pytest src/tests

.PHONY: docker-run
docker-run: ## Run project (bot) in docker (using docker compose)
	@echo Run project in docker...
	docker compose up --build bot

.PHONY: docker-test
docker-test: ## Run tests in docker (using docker compose)
	@echo Test project in docker...
	docker compose up --build test

.PHONY: locale-init
locale-init: ## Locale: init i18n files
	@echo Localization: init...
	xgettext -o src/i18n/messages.pot src/handlers/*.py src/cli/*.py
	msginit -i src/i18n/messages.pot -o src/i18n/ru/LC_MESSAGES/messages.po -l ru_RU.UTF-8 --no-translator

.PHONY: locale-update
locale-update: ## Locale: update i18n files with new tokens
	@echo Localization: update tokens...
	xgettext -o src/i18n/messages.pot src/handlers/*.py src/cli/*.py
	msgmerge --update src/i18n/ru/LC_MESSAGES/messages.po src/i18n/messages.pot

.PHONY: locale-compile
locale-compile: ## Locale: compile filled translations for using
	@echo Localization: complie translations...
	msgfmt -o src/i18n/ru/LC_MESSAGES/messages.mo src/i18n/ru/LC_MESSAGES/messages.po
