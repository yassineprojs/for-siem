# Lightweight Python runtime
FROM python:3.11-slim

RUN useradd -ms /bin/bash appuser
WORKDIR /app

COPY pyproject.toml README.md ./
COPY ey_cs_monitor ./ey_cs_monitor
COPY config.example.yaml ./

RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir .

USER appuser
ENTRYPOINT ["ey-cs-monitor"]
CMD ["--config", "/app/config.yaml"]
