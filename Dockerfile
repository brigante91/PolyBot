FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/polymarket_bot

COPY pyproject.toml README.md requirements.txt ./
COPY polymarket_bot ./polymarket_bot
COPY tests ./tests

RUN pip install --no-cache-dir -e ".[dev]"

RUN mkdir -p data outputs

CMD ["python", "-m", "app.cli", "--help"]
