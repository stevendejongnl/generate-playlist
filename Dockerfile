FROM python:3.12-slim AS base

WORKDIR /app

RUN pip install --no-cache-dir uv

# Install Python dependencies
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen

# Install Node dependencies and build frontend
FROM node:22-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json vite.config.ts ./
COPY frontend/ frontend/
RUN npm run build

# Final image
FROM base
COPY . .
COPY --from=frontend /app/static/js/app.iife.js static/js/app.iife.js

RUN mkdir -p /app/data

CMD ["uv", "run", "uvicorn", "playlist_generator.main:app", "--host", "0.0.0.0", "--port", "5000"]
