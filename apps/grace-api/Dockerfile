FROM node:20-bookworm-slim AS nodekit
WORKDIR /opt/kits/lambda-lifeline
COPY kits/lambda-lifeline/package*.json ./
RUN npm ci --omit=dev
COPY kits/lambda-lifeline ./
RUN npm link

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libharfbuzz0b \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

COPY apps/grace-api/requirements.txt /tmp/grace-api-requirements.txt
COPY apps/runner/requirements.txt /tmp/runner-requirements.txt
RUN pip install --no-cache-dir -r /tmp/grace-api-requirements.txt -r /tmp/runner-requirements.txt

COPY kits/al2023-gate /opt/kits/al2023-gate
COPY kits/python-pivot /opt/kits/python-pivot
RUN pip install --no-cache-dir /opt/kits/al2023-gate /opt/kits/python-pivot

COPY --from=nodekit /usr/local/bin/lambda-lifeline /usr/local/bin/lambda-lifeline
COPY --from=nodekit /usr/local/lib/node_modules/lambda-lifeline /usr/local/lib/node_modules/lambda-lifeline

COPY apps/runner /app/runner
COPY apps/grace-api/eolkits_grace /app/eolkits_grace
# pricing.py is the single source of truth for SKU -> Price IDs + surge tiers and
# is read at request time; it must be present in the image.
COPY pricing.yml /app/pricing.yml

ENV PYTHONPATH=/app:/app/runner
ENV EOLKITS_DATA_DIR=/data/eolkits
ENV EOLKITS_PRICING_FILE=/app/pricing.yml
EXPOSE 8080

CMD ["uvicorn", "eolkits_grace.app:app", "--host", "0.0.0.0", "--port", "8080"]
