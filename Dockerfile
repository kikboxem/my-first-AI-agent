# Ubuntu 26.04 LTS (Resolute Raccoon) - deterministic, auditable runtime.
FROM ubuntu:26.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

COPY app.py server.py index.html styles.css agent_ui.js csv_audit.js csv_ui.js social-preview.png /app/

# Run without privileges; no root needed at runtime.
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin valuepilot \
    && chown -R valuepilot:valuepilot /app
USER 10001:10001

EXPOSE 10000

# Health checks do not use model inference or consume Redis quotas.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:10000/health', timeout=3)" || exit 1

CMD ["python", "app.py"]
