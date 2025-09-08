FROM python:3.8-slim-buster

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock* ./
COPY .env ./
RUN poetry install --no-interaction --no-ansi
RUN poetry --version && poetry install --no-interaction --no-ansi
COPY . .

RUN mkdir -p /app/.cache

CMD [ "poetry", "run", "python", "-m", "playlist_generator.main" ]