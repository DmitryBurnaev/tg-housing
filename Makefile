lint:
	poetry run ruff check
	poetry run mypy .

format:
	poetry run ruff format

upgrade:
	poetry update

run:
	PYTHONPATH=. poetry run python src/main.py

test:
	PYTHONPATH=. poetry run pytest src/tests

docker-run:
	docker compose up --build bot

docker-test:
	docker compose up --build test

locale-init:
	xgettext -o src/i18n/messages.pot src/handlers/*.py
	msginit -i src/i18n/messages.pot -o src/i18n/ru/LC_MESSAGES/messages.po -l ru_RU.UTF-8 --no-translator

locale-update:
	xgettext -o src/i18n/messages.pot src/handlers/*.py
	msgmerge --update src/i18n/ru/LC_MESSAGES/messages.po src/i18n/messages.pot

locale-compile:
	msgfmt -o src/i18n/ru/LC_MESSAGES/messages.mo src/i18n/ru/LC_MESSAGES/messages.po
