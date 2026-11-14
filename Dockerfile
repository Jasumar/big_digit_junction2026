# S-pankki coach: one container serving the API and the static UI (apps/bank-backend/server.py).
# Standard library only, so there is no dependency install step.
#
# Built by Aiven Runtime from this repo (README.md §Deploy), or locally:
#   docker build -t spankki-coach .                           # full dataset (~0.5 GB database)
#   docker build -t spankki-coach --build-arg DATA=fixture .  # 6-customer sample, seconds
#   docker run --rm -p 8080:8080 --env-file .env spankki-coach
#
# The AI runs elsewhere (Modal or OpenRouter): set AI_PROVIDER and its key as runtime
# environment variables / secrets. Never put keys in this file or in the image.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Data first, so a code change does not rebuild the database layer.
# DATA=full: download the four hackathon CSVs, build the database, and delete the CSVs in
# the same layer. DATA=fixture: build the committed 6-customer sample.
# The database is read-only at run time (store.py opens it with mode=ro).
ARG DATA=full
COPY packages/cloud/ packages/cloud/
RUN set -eux; \
    if [ "$DATA" = "full" ]; then \
      python packages/cloud/fetch_data.py; \
      python packages/cloud/seed.py --full; \
      rm -rf packages/cloud/data/raw; \
    else \
      python packages/cloud/seed.py; \
    fi

COPY apps/ apps/
COPY packages/ packages/

# Run as a non-root user; files stay root-owned and readable, nothing is written at run time.
RUN useradd --system --uid 10001 --no-create-home app
USER app

# Aiven Runtime reads the port from EXPOSE and terminates TLS in front of it.
ENV HOST=0.0.0.0 \
    PORT=8080 \
    AI_PROVIDER=stub
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT', '8080'), timeout=4)"]

CMD ["python", "apps/bank-backend/server.py"]
