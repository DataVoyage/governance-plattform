# Frontend als statisch ausgelieferte Single-Page-Application (Architektur 6.1).
#
# Der Bau laeuft ueber dem Wurzelverzeichnis des Repositorys, nicht ueber
# `frontend/`. Grund ist die Konzeptvorstellung: sie liegt als **eine** Quelle
# in `docs/` — lesbar im Repository, projizierbar ueber Marp, und dieselbe
# Datei traegt die Ansicht in der Anwendung. Eine Kopie im Frontend waere
# genau die Doppelpflege, die dieses Vorhaben sonst ueberall vermeidet.
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

FROM ${GP_BASIS_PRAEFIX}node:22-bookworm-slim AS build

WORKDIR /bau/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Nur das, was die Anwendung wirklich einliest — nicht das ganze Verzeichnis.
COPY docs/praesentation.md /bau/docs/praesentation.md
COPY docs/bilder/ /bau/docs/bilder/
ARG VITE_API_BASIS=""
ENV VITE_API_BASIS=$VITE_API_BASIS
ARG VITE_BASIS_PFAD="/"
ENV VITE_BASIS_PFAD=$VITE_BASIS_PFAD
RUN npm run build


FROM ${GP_BASIS_PRAEFIX}nginx:1.27-alpine AS runtime
COPY --from=build /bau/frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
