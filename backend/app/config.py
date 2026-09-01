"""Technische Konfiguration (ENV-Ebene, Architektur Abschnitt 6.6).

Hier stehen ausschliesslich Einstellungen, die *wie* die Anwendung laeuft
betreffen. Inhaltliche Governance-Einstellungen (Fristen, Schwellen,
Erinnerungsvorlauf) liegen in der Tabelle ``konfiguration`` und werden ueber
``app.services.konfiguration`` gelesen — nie ueber ENV.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GP_", env_file=".env", extra="ignore")

    # --- Datenbank -----------------------------------------------------
    database_url: str = "postgresql+psycopg://governance:governance@localhost:5432/governance"

    # --- Identitaet (Abschnitt 10.1) ------------------------------------
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_jwks_url: str = ""
    oidc_audience: str = ""

    # Entwicklungs-/Testmodus: erlaubt lokal ausgestellte HS256-Tokens statt
    # eines echten OIDC-Providers. In Produktion immer false.
    auth_dev_mode: bool = False
    auth_dev_secret: str = "dev-secret-not-for-production"

    # Erstzugang: kommaseparierte OIDC-Subjects, die bei ihrer ersten Anmeldung
    # die Rollen App-Administrator und Governance global erhalten. Ohne diesen
    # Startpunkt koennte niemand die erste Rollenzuweisung vornehmen, weil
    # Rollen nur ein App-Administrator vergibt (Architektur 5.3).
    bootstrap_admin_subjects: str = ""

    # --- Service-Authentifizierung der Query-API (Abschnitt 10.3) -------
    # Kommaseparierte Liste ``name:token``-Paare fuer andockende Anwendungen.
    query_api_service_tokens: str = ""

    # --- Betrieb --------------------------------------------------------
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"
    ca_bundle_path: str = ""
    image_registry: str = "localhost:5000"

    @property
    def bootstrap_admin_list(self) -> list[str]:
        return [s.strip() for s in self.bootstrap_admin_subjects.split(",") if s.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def service_token_map(self) -> dict[str, str]:
        """Mapping Token -> Name der andockenden Anwendung."""
        result: dict[str, str] = {}
        for entry in self.query_api_service_tokens.split(","):
            entry = entry.strip()
            if not entry or ":" not in entry:
                continue
            name, _, token = entry.partition(":")
            if name.strip() and token.strip():
                result[token.strip()] = name.strip()
        return result


@lru_cache
def get_settings() -> Settings:
    return Settings()
