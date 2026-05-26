setup:
	cp -n .env.example .env || true
	docker compose build

dev:
	docker compose up

migrate:
	docker compose run --rm backend python manage.py migrate

test:
	docker compose run --rm backend pytest

ingest-demo:
	docker compose run --rm backend python manage.py ingest_youtube_url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
