FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["sh", "-c", "python -m app.seeds.cli && uvicorn app.main:app --host 0.0.0.0 --port 8000"]