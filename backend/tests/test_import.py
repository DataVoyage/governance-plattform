"""Import-/Sync-API — Abnahmekriterium Phase 1.2 (Architektur 7.2)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def plattform(anmelden, rolle_geben):
    nutzer = anmelden("Plattform", subject="sub-plattform")
    rolle_geben(nutzer.user_id, "plattform", "global")
    return nutzer


QUELLE = "zentrale-entwicklungsplattform"

STAMMDATEN = [
    {
        "typ": "fachbereich",
        "externe_id": "FB-FIN",
        "name": "Finance",
        "metadaten": {"code": "fb-fin"},
    },
    {
        "typ": "organisationseinheit",
        "externe_id": "OE-FIN-INT",
        "name": "Finance International",
        "metadaten": {"fachbereich_externe_id": "FB-FIN", "ebene": "INT"},
    },
    {
        "typ": "organisationseinheit",
        "externe_id": "OE-FIN-DE",
        "name": "Finance Deutschland",
        "metadaten": {"fachbereich_externe_id": "FB-FIN", "ebene": "LAND", "land_code": "de"},
    },
    {
        "typ": "organisationseinheit",
        "externe_id": "OE-FIN-FR",
        "name": "Finance Frankreich",
        "metadaten": {"fachbereich_externe_id": "FB-FIN", "ebene": "LAND", "land_code": "FR"},
    },
    {
        "typ": "team",
        "externe_id": "TEAM-AP",
        "name": "Accounts Payable",
        "owner_hinweis": "ap.lead@beispiel-ag.de",
        "metadaten": {"organisationseinheit_externe_id": "OE-FIN-DE"},
    },
]


def importiere(client: TestClient, plattform, datensaetze, quelle: str = QUELLE):
    return client.post(
        "/api/v1/import/assets",
        json={"quelle": quelle, "datensaetze": datensaetze},
        headers=plattform.kopf,
    )


def test_import_legt_stammdaten_an(client: TestClient, plattform, db) -> None:
    from app.models.enums import Ebene
    from app.models.organisation import Fachbereich, Organisationseinheit, Team

    antwort = importiere(client, plattform, STAMMDATEN)
    assert antwort.status_code == 200, antwort.text
    ergebnis = antwort.json()
    assert ergebnis["angelegt"] == 5
    assert ergebnis["fehler"] == []

    db.expire_all()
    assert db.query(Fachbereich).count() == 1
    einheiten = db.query(Organisationseinheit).all()
    assert len(einheiten) == 3
    assert {e.land_code for e in einheiten if e.ebene == Ebene.LAND} == {"DE", "FR"}
    team = db.query(Team).one()
    assert team.owner_hinweis == "ap.lead@beispiel-ag.de"
    assert team.organisationseinheit_id is not None


def test_zweiter_lauf_erzeugt_keine_duplikate(client: TestClient, plattform, db) -> None:
    """Abnahmekriterium 1.2: unveraenderte Quelldaten, keine Duplikate."""
    from app.models.organisation import Fachbereich, Organisationseinheit, Team

    importiere(client, plattform, STAMMDATEN)
    zweiter = importiere(client, plattform, STAMMDATEN).json()
    assert zweiter["angelegt"] == 0
    assert zweiter["aktualisiert"] == 0
    assert zweiter["unveraendert"] == 5

    db.expire_all()
    assert db.query(Fachbereich).count() == 1
    assert db.query(Organisationseinheit).count() == 3
    assert db.query(Team).count() == 1


def test_geaenderte_quelldaten_werden_uebernommen(client: TestClient, plattform, db) -> None:
    from app.models.organisation import Fachbereich

    importiere(client, plattform, STAMMDATEN)
    geaendert = [dict(STAMMDATEN[0], name="Finance & Controlling")]
    ergebnis = importiere(client, plattform, geaendert).json()
    assert ergebnis["aktualisiert"] == 1
    db.expire_all()
    assert db.query(Fachbereich).one().name == "Finance & Controlling"


def test_namensdublette_wird_nur_vorgeschlagen(client: TestClient, plattform, db) -> None:
    """Ambige Faelle werden nie automatisch zusammengefuehrt (Architektur 7.2)."""
    from app.models.organisation import Fachbereich

    importiere(client, plattform, [STAMMDATEN[0]])
    ergebnis = importiere(
        client,
        plattform,
        [{"typ": "fachbereich", "externe_id": "FIN", "name": "finance", "metadaten": {}}],
        quelle="andere-quelle",
    ).json()
    assert ergebnis["angelegt"] == 0
    assert len(ergebnis["vorschlaege"]) == 1
    vorschlag = ergebnis["vorschlaege"][0]
    assert vorschlag["kandidat_name"] == "Finance"
    db.expire_all()
    assert db.query(Fachbereich).count() == 1


def test_unbekannter_verweis_wird_als_fehler_gemeldet(client: TestClient, plattform) -> None:
    ergebnis = importiere(
        client,
        plattform,
        [
            {
                "typ": "organisationseinheit",
                "externe_id": "OE-X",
                "name": "Ohne Fachbereich",
                "metadaten": {"fachbereich_externe_id": "FEHLT", "ebene": "INT"},
            }
        ],
    ).json()
    assert ergebnis["angelegt"] == 0
    assert ergebnis["fehler"][0]["externe_id"] == "OE-X"


@pytest.mark.parametrize(
    ("metadaten", "textteil"),
    [
        ({"ebene": "INT"}, "fachbereich_externe_id"),
        ({"fachbereich_externe_id": "FB-FIN", "ebene": "REGION"}, "ebene"),
        ({"fachbereich_externe_id": "FB-FIN", "ebene": "LAND"}, "land_code"),
    ],
)
def test_fehlerhafte_organisationseinheiten(
    client: TestClient, plattform, metadaten: dict, textteil: str
) -> None:
    importiere(client, plattform, [STAMMDATEN[0]])
    ergebnis = importiere(
        client,
        plattform,
        [
            {
                "typ": "organisationseinheit",
                "externe_id": "OE-F",
                "name": "F",
                "metadaten": metadaten,
            }
        ],
    ).json()
    assert textteil in ergebnis["fehler"][0]["grund"]


def test_team_mit_unbekannter_einheit(client: TestClient, plattform) -> None:
    ergebnis = importiere(
        client,
        plattform,
        [
            {
                "typ": "team",
                "externe_id": "T-1",
                "name": "Waisen-Team",
                "metadaten": {"organisationseinheit_externe_id": "GIBT-ES-NICHT"},
            }
        ],
    ).json()
    assert ergebnis["fehler"][0]["grund"].startswith("Organisationseinheit")


def test_team_ohne_einheit_ist_erlaubt(client: TestClient, plattform, db) -> None:
    from app.models.organisation import Team

    ergebnis = importiere(
        client, plattform, [{"typ": "team", "externe_id": "T-2", "name": "Freies Team"}]
    ).json()
    assert ergebnis["angelegt"] == 1
    db.expire_all()
    assert db.query(Team).one().organisationseinheit_id is None


def test_import_ist_der_plattform_rolle_vorbehalten(client: TestClient, anmelden) -> None:
    fremder = anmelden("Ohne Rolle")
    antwort = client.post(
        "/api/v1/import/assets",
        json={"quelle": QUELLE, "datensaetze": []},
        headers=fremder.kopf,
    )
    assert antwort.status_code == 403


def test_unbekannte_felder_werden_abgelehnt(client: TestClient, plattform) -> None:
    antwort = importiere(
        client,
        plattform,
        [{"typ": "team", "externe_id": "T-3", "name": "X", "geheim": "wert"}],
    )
    assert antwort.status_code == 422


def test_import_wird_protokolliert(client: TestClient, plattform, db) -> None:
    from app.models.audit import ChangeLog

    importiere(client, plattform, [STAMMDATEN[0]])
    db.expire_all()
    eintrag = db.query(ChangeLog).filter(ChangeLog.entity_type == "fachbereiche").one()
    assert eintrag.aktion == "erstellt"
    assert eintrag.akteur_beschreibung == f"Import aus {QUELLE}"
