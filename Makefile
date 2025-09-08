.PHONY: help docker-build docker-run poetry-update poetry-lock run-local

help:
	@echo "Available targets:"
	@echo "  docker-build    Build the Docker image (playlist-generator)"
	@echo "  docker-run      Run the Docker container (playlist-generator)"
	@echo "  poetry-update   Update all Python packages via Poetry (in Docker)"
	@echo "  poetry-lock     Regenerate poetry.lock file via Poetry (in Docker)"
	@echo "  pytest          Run tests inside the Docker container using Poetry"

docker-build:
	docker build -t playlist-generator .

docker-run:
	docker run --rm -it -p 5000:5000 -e FLASK_DEBUG=1 -v $(PWD)/data:/app/data -v $(PWD)/.cache:/app/.cache playlist-generator

poetry-update:
	docker run --rm -it -v $(PWD):/src -w /src playlist-generator poetry update

poetry-lock:
	docker run --rm -it -v $(PWD):/src -w /src playlist-generator poetry lock

pytest:
	docker run --rm -it -v $(PWD):/src -w /src playlist-generator poetry run pytest
