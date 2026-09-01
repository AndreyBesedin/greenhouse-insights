FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN pip install --no-cache-dir "poetry>=2.0,<3"

WORKDIR /app

# Dependencies in their own layer, cached separately from app code so an
# app-only change does not trigger a full reinstall.
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

COPY . .
RUN poetry install --only main

RUN useradd --create-home --shell /bin/false appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "application.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
