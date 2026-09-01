"""Tokenpruefung (Architektur 10.1) und Sync-Worker (6.1)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import pytest
from jose import jwt

from app.config import Settings
from app.core.permissions import Principal, Verboten, Zuweisung, verlange
from app.core.security import (
    AuthError,
    claims_to_identity,
    clear_jwks_cache,
    issue_dev_token,
    verify_token,
)
from app.models.enums import Rolle, ScopeTyp
from app.sync import worker


@pytest.fixture
def dev_settings() -> Settings:
    return Settings(auth_dev_mode=True, auth_dev_secret="geheim")


def test_dev_token_rundlauf(dev_settings: Settings) -> None:
    token = issue_dev_token(dev_settings, "sub-1", "a@beispiel-ag.de", "A")
    claims = verify_token(token, dev_settings)
    assert claims_to_identity(claims) == ("sub-1", "a@beispiel-ag.de", "A")


def test_dev_token_nur_im_entwicklungsmodus() -> None:
    with pytest.raises(AuthError):
        issue_dev_token(Settings(auth_dev_mode=False), "s", "a@beispiel-ag.de", "A")


def test_token_mit_falschem_geheimnis(dev_settings: Settings) -> None:
    token = issue_dev_token(dev_settings, "sub-1", "a@beispiel-ag.de", "A")
    with pytest.raises(AuthError):
        verify_token(token, Settings(auth_dev_mode=True, auth_dev_secret="anderes"))


def test_abgelaufenes_token(dev_settings: Settings) -> None:
    claims = {
        "sub": "s",
        "aud": "governance-plattform",
        "iss": "governance-plattform-dev",
        "exp": int(time.time()) - 10,
    }
    token = jwt.encode(claims, dev_settings.auth_dev_secret, algorithm="HS256")
    with pytest.raises(AuthError):
        verify_token(token, dev_settings)


def test_ohne_oidc_konfiguration_kein_produktivbetrieb() -> None:
    with pytest.raises(AuthError, match="OIDC"):
        verify_token("egal", Settings(auth_dev_mode=False))


def test_claims_ohne_subject() -> None:
    with pytest.raises(AuthError):
        claims_to_identity({"email": "a@beispiel-ag.de"})


def test_claims_ergaenzen_fehlende_felder() -> None:
    subject, email, name = claims_to_identity({"sub": "s-9"})
    assert subject == "s-9"
    assert email.startswith("s-9@")
    assert name == email


def test_jwks_wird_zwischengespeichert(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import security

    aufrufe = {"n": 0}

    class Antwort:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"keys": []}

    def fake_get(url: str, *, timeout: float) -> Antwort:
        aufrufe["n"] += 1
        return Antwort()

    clear_jwks_cache()
    monkeypatch.setattr(security.httpx, "get", fake_get)
    assert security._fetch_jwks("https://idp.invalid/jwks") == {"keys": []}
    assert security._fetch_jwks("https://idp.invalid/jwks") == {"keys": []}
    assert aufrufe["n"] == 1
    clear_jwks_cache()


def test_oidc_pfad_ohne_passenden_schluessel(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import security

    class Antwort:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"keys": []}

    clear_jwks_cache()
    monkeypatch.setattr(security.httpx, "get", lambda url, **kw: Antwort())
    settings = Settings(
        auth_dev_mode=False,
        oidc_jwks_url="https://idp.invalid/jwks",
        oidc_issuer="https://idp.invalid",
        oidc_audience="governance",
    )
    token = jwt.encode({"sub": "s"}, "irgendwas", algorithm="HS256")
    with pytest.raises(AuthError):
        verify_token(token, settings)
    clear_jwks_cache()


# --- Konfigurationsableitungen -------------------------------------------


def test_service_token_map_ignoriert_unvollstaendige_eintraege() -> None:
    settings = Settings(query_api_service_tokens="a:1, kaputt , :2, b:3,")
    assert settings.service_token_map == {"1": "a", "3": "b"}


def test_cors_liste() -> None:
    assert Settings(cors_origins="http://a, http://b ,").cors_origin_list == [
        "http://a",
        "http://b",
    ]


# --- Principal ------------------------------------------------------------


def test_principal_scopes_und_kurzformen() -> None:
    import uuid

    org = uuid.uuid4()
    fb = uuid.uuid4()
    principal = Principal(
        user_id=uuid.uuid4(),
        email="a@beispiel-ag.de",
        name="A",
        zuweisungen=[
            Zuweisung(Rolle.PROZESS_OWNER, ScopeTyp.ORGANISATIONSEINHEIT, org),
            Zuweisung(Rolle.TECHNISCHER_OWNER, ScopeTyp.FACHBEREICH, fb),
        ],
    )
    assert principal.scope_organisationseinheiten == {org}
    assert principal.scope_fachbereiche == {fb}
    assert principal.hat_rolle(Rolle.PROZESS_OWNER, organisationseinheit_id=org)
    assert not principal.hat_rolle(Rolle.PROZESS_OWNER, organisationseinheit_id=uuid.uuid4())
    assert principal.hat_rolle(Rolle.TECHNISCHER_OWNER, fachbereich_id=fb)
    assert principal.hat_rolle(Rolle.PROZESS_OWNER)
    assert not principal.sieht_global
    assert not principal.ist_governance
    assert not principal.ist_auditor
    assert not principal.ist_plattform
    assert not principal.ist_administrator


def test_globaler_scope_schlaegt_bereichsangabe() -> None:
    import uuid

    principal = Principal(
        user_id=uuid.uuid4(),
        email="g@beispiel-ag.de",
        name="G",
        zuweisungen=[Zuweisung(Rolle.GOVERNANCE, ScopeTyp.GLOBAL)],
    )
    assert principal.hat_rolle(Rolle.GOVERNANCE, organisationseinheit_id=uuid.uuid4())
    assert principal.sieht_global
    assert principal.ist_governance


def test_verlange_wirft_verboten() -> None:
    with pytest.raises(Verboten, match="Grund"):
        verlange(False, "Grund")
    verlange(True)


# --- Sync-Worker ----------------------------------------------------------


def test_worker_liest_datei_und_sendet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    nutzlast = {"quelle": "q", "datensaetze": []}
    datei = tmp_path / "export.json"
    datei.write_text(json.dumps(nutzlast), encoding="utf-8")

    gesendet: dict = {}

    class Antwort:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"angelegt": 1, "aktualisiert": 0, "unveraendert": 0}

    def fake_post(url: str, *, json: dict, headers: dict, timeout: float, verify) -> Antwort:
        gesendet.update({"url": url, "json": json, "headers": headers, "verify": verify})
        return Antwort()

    monkeypatch.setattr(worker.httpx, "post", fake_post)
    code = worker.main(
        ["--api", "http://backend", "--token", "t", "--datei", str(datei), "--ca-bundle", "/ca.pem"]
    )
    assert code == 0
    assert gesendet["url"] == "http://backend/api/v1/import/assets"
    assert gesendet["json"] == nutzlast
    assert gesendet["verify"] == "/ca.pem"


def test_worker_meldet_fehler_als_exitcode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    datei = tmp_path / "export.json"
    datei.write_text(json.dumps({"quelle": "q", "datensaetze": []}), encoding="utf-8")

    class Antwort:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"fehler": [{"externe_id": "x", "grund": "kaputt"}]}

    monkeypatch.setattr(worker.httpx, "post", lambda *a, **kw: Antwort())
    assert worker.main(["--api", "http://b", "--token", "t", "--datei", str(datei)]) == 1


def test_worker_ohne_quelle(capsys: pytest.CaptureFixture[str]) -> None:
    assert worker.main(["--api", "http://b", "--token", "t"]) == 2


def test_worker_holt_von_http(monkeypatch: pytest.MonkeyPatch) -> None:
    class Antwort:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"quelle": "q", "datensaetze": []}

    gesehen: dict = {}

    def fake_get(url: str, *, headers: dict, timeout: float, verify) -> Antwort:
        gesehen.update({"url": url, "headers": headers})
        return Antwort()

    monkeypatch.setattr(worker.httpx, "get", fake_get)
    monkeypatch.setattr(worker.httpx, "post", lambda *a, **kw: Antwort())
    code = worker.main(
        ["--api", "http://b", "--token", "t", "--url", "http://quelle", "--quell-token", "qt"]
    )
    assert code == 0
    assert gesehen["headers"]["Authorization"] == "Bearer qt"


def test_worker_reicht_http_fehler_durch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    datei = tmp_path / "e.json"
    datei.write_text("{}", encoding="utf-8")

    def fake_post(*args, **kwargs):
        raise httpx.HTTPError("Netz weg")

    monkeypatch.setattr(worker.httpx, "post", fake_post)
    with pytest.raises(httpx.HTTPError):
        worker.main(["--api", "http://b", "--token", "t", "--datei", str(datei)])
