FROM python:3.12

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock* ./
RUN poetry --version && poetry install --no-interaction --no-ansi --no-root
COPY . .

RUN mkdir -p /app/.cache

CMD [ "poetry", "run", "python", "-m", "playlist_generator.main" ]
