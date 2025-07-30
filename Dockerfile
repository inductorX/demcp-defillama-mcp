FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

COPY . .

EXPOSE 8090
CMD ["uv", "run", "python", "defillama.py"]