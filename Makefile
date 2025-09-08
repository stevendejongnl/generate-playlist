.PHONY: help docker-build docker-run poetry-update poetry-lock run-local

help:
	@echo "Available targets:"
	@echo "  docker-build    Build the Docker image (generate-playlist)"
	@echo "  docker-run      Run the Docker container (generate-playlist)"
	@echo "  poetry-update   Update all Python packages via Poetry (in Docker)"
	@echo "  poetry-lock     Regenerate poetry.lock file via Poetry (in Docker)"

docker-build:
	docker build -t generate-playlist .

docker-run:
	docker run --rm -it -p 5000:5000 -e FLASK_DEBUG=1 -v $(PWD)/data:/app/data -v $(PWD)/.cache:/app/.cache generate-playlist

poetry-update:
	docker run --rm -it -v $(PWD):/src -w /src generate-playlist poetry update

poetry-lock:
	docker run --rm -it -v $(PWD):/src -w /src generate-playlist poetry lock
