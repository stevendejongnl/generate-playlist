FROM python:3.12

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen

COPY . .

RUN mkdir -p /app/.cache

CMD [ "uv", "run", "uvicorn", "playlist_generator.main:app", "--host", "0.0.0.0", "--port", "5000" ]
