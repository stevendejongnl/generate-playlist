FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl build-essential libffi-dev \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

COPY pyproject.toml poetry.lock* ./
COPY .env ./
COPY . .

ENV POETRY_VIRTUALENVS_CREATE=false
RUN poetry install --no-interaction --no-ansi --with=dev

RUN mkdir -p /app/.cache

CMD [ "poetry", "run", "python", "-m", "playlist_generator.main" ]