FROM python:3.11-slim

ENV POETRY_VERSION=1.7.1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install "poetry==${POETRY_VERSION}" && mkdir -p /app
WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
