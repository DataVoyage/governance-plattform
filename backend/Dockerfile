# Mehrstufiger Build (Architektur 6.5): eine Build-Stage mit `uv sync` gegen die
# Lockfile, ein schlankes Runtime-Image ohne Build-Werkzeuge.
# Woher die Basisimages kommen. Leer heisst Docker Hub beziehungsweise ghcr.io;
# in einer Umgebung ohne Zugang dorthin zeigen beide auf den internen Spiegel:
#
#   GP_BASIS_PRAEFIX=artifactory.beispiel-ag.de/docker-remote/
#   GP_GHCR_PRAEFIX=artifactory.beispiel-ag.de/ghcr-remote/
#
# Der abschliessende Schraegstrich gehoert zum Wert — nur so bleibt der
# Vorgabewert leer und der Name unveraendert. Zwei Variablen, weil Docker Hub
# und ghcr.io in Artifactory ueblicherweise getrennte Remote-Repositories sind;
# bei einem virtuellen Repository, das beide buendelt, bekommen sie denselben
# Wert. Analog zu GP_IMAGE_REGISTRY steht keine Adresse im Code.
ARG GP_BASIS_PRAEFIX=""
ARG GP_GHCR_PRAEFIX="ghcr.io/"

FROM ${GP_GHCR_PRAEFIX}astral-sh/uv:python3.12-bookworm-slim AS build

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Optionales CA-Bundle einer internen Zertifizierungsstelle: wird, falls
# vorhanden, vor dem Abhaengigkeitsauflösen in den Truststore gelegt — relevant
# fuer ein internes Paket-Mirror beim `uv sync`.
ARG EXTRA_CA_BUNDLE=""
COPY ca/ /tmp/ca/
RUN if [ -n "$EXTRA_CA_BUNDLE" ] && [ -f "/tmp/ca/$EXTRA_CA_BUNDLE" ]; then \
      cp "/tmp/ca/$EXTRA_CA_BUNDLE" /usr/local/share/ca-certificates/intern.crt && \
      update-ca-certificates; \
    fi

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
RUN uv sync --frozen --no-dev


FROM ${GP_BASIS_PRAEFIX}python:3.12-slim-bookworm AS runtime

RUN useradd --create-home --uid 10001 governance
WORKDIR /app

COPY --from=build /app /app
COPY --from=build /usr/local/share/ca-certificates/ /usr/local/share/ca-certificates/
RUN update-ca-certificates || true

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER governance
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
