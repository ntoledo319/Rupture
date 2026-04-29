# Rupture Runner Container
# Multi-stage build for the job runner that processes audit PDFs and migration PRs

FROM python:3.14-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.14-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Install all three kits
COPY kits/lambda-lifeline /opt/kits/lambda-lifeline
COPY kits/al2023-gate /opt/kits/al2023-gate
COPY kits/python-pivot /opt/kits/python-pivot

RUN pip install --no-cache-dir \
    /opt/kits/lambda-lifeline \
    /opt/kits/al2023-gate \
    /opt/kits/python-pivot

# Copy runner code
COPY apps/runner/main.py /app/
COPY apps/runner/audit_pdf.py /app/
COPY apps/runner/migration_pr.py /app/

# Make sure scripts are in PATH
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "/app/main.py"]
