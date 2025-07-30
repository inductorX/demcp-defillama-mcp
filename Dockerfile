FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:${PATH}"

COPY . .

RUN uv venv
RUN uv pip install -e .

EXPOSE 8090
CMD ["uv", "run", "defillama.py"]