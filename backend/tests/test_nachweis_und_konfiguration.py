"""Nachweis (Architektur 10.4) und inhaltliche Konfiguration (6.6)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import ChangeAktion
from app.services import changelog, konfiguration


@pytest.fixture
def governance(anmelden, rolle_geben):
    nutzer = anmelden("Governance", subject="sub-gov")
    rolle_geben(nutzer.user_id, "governance", "global")
    return nutzer


# --- change_log ----------------------------------------------------------


def test_cursor_steigt_monoton(db: Session) -> None:
    import uuid

    eintraege = [
        changelog.protokolliere(
            db,
            entity_type="prozessobjekte",
            entity_id=uuid.uuid4(),
            aktion=ChangeAktion.ERSTELLT,
            nachher={"i": i},
        )
        for i in range(5)
    ]
    cursors = [e.cursor for e in eintraege]
    assert cursors == sorted(cursors)
    assert len(set(cursors)) == 5


def test_delta_abfrage_ist_zustandslos(db: Session) -> None:
    import uuid

    for i in range(3):
        changelog.protokolliere(
            db,
            entity_type="bewertungen",
            entity_id=uuid.uuid4(),
            aktion=ChangeAktion.ERSTELLT,
            nachher={"i": i},
        )
    alle = changelog.eintraege_seit(db, since=0)
    assert len(alle) == 3
    ab_erstem = changelog.eintraege_seit(db, since=alle[0].cursor)
    assert [e.cursor for e in ab_erstem] == [alle[1].cursor, alle[2].cursor]
    # Derselbe Cursor liefert erneut dasselbe Ergebnis.
    assert [e.cursor for e in changelog.eintraege_seit(db, since=alle[0].cursor)] == [
        e.cursor for e in ab_erstem
    ]


def test_delta_abfrage_filtert_nach_typ(db: Session) -> None:
    import uuid

    changelog.protokolliere(
        db, entity_type="bewertungen", entity_id=uuid.uuid4(), aktion=ChangeAktion.ERSTELLT
    )
    changelog.protokolliere(
        db, entity_type="tool_objekte", entity_id=uuid.uuid4(), aktion=ChangeAktion.ERSTELLT
    )
    treffer = changelog.eintraege_seit(db, since=0, entity_types=["tool_objekte"])
    assert [e.entity_type for e in treffer] == ["tool_objekte"]


def test_aenderung_ohne_inhalt_erzeugt_keinen_eintrag(db: Session, organisation) -> None:
    from app.models.organisation import Fachbereich

    fachbereich = db.query(Fachbereich).filter(Fachbereich.code == "fb-fin").one()
    vorher = changelog.snapshot(fachbereich)
    assert changelog.protokolliere_aenderung(db, fachbereich, vorher) is None
    fachbereich.name = "Finance neu"
    assert changelog.protokolliere_aenderung(db, fachbereich, vorher) is not None


def test_diff_zeigt_nur_veraenderte_felder() -> None:
    ergebnis = changelog.diff({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 4})
    assert ergebnis == {"b": {"vorher": 2, "nachher": 3}, "c": {"vorher": None, "nachher": 4}}


def test_snapshot_ist_json_sicher(db: Session, organisation) -> None:
    import json

    from app.models.organisation import Organisationseinheit

    einheit = db.query(Organisationseinheit).first()
    json.dumps(changelog.snapshot(einheit))


def test_loeschung_wird_protokolliert(db: Session, organisation) -> None:
    from app.models.audit import ChangeLog
    from app.models.organisation import Fachbereich

    fachbereich = db.query(Fachbereich).filter(Fachbereich.code == "fb-hr").one()
    changelog.protokolliere_loeschung(db, fachbereich)
    eintrag = db.query(ChangeLog).filter(ChangeLog.entity_id == fachbereich.id).one()
    assert eintrag.aktion == ChangeAktion.GELOESCHT
    assert eintrag.nachher is None


def test_prozessanlage_landet_im_nachweis(
    client: TestClient, anmelden, rolle_geben, organisation, prozess_daten, db
) -> None:
    from app.models.audit import ChangeLog

    owner = anmelden("Owner")
    rolle_geben(owner.user_id, "prozess_owner", "organisationseinheit", organisation["fin_int"])
    vertretung = anmelden("Vertretung")
    angelegt = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    ).json()
    client.patch(f"/api/v1/prozesse/{angelegt['id']}", json={"name": "Anders"}, headers=owner.kopf)
    db.expire_all()
    eintraege = (
        db.query(ChangeLog)
        .filter(ChangeLog.entity_type == "prozessobjekte")
        .order_by(ChangeLog.cursor)
        .all()
    )
    assert [e.aktion for e in eintraege] == [ChangeAktion.ERSTELLT, ChangeAktion.GEAENDERT]
    assert eintraege[1].vorher["name"] == "Rechnungspruefung"
    assert eintraege[1].nachher["name"] == "Anders"


# --- Konfiguration -------------------------------------------------------


def test_standardwerte_werden_einmalig_angelegt(db: Session) -> None:
    assert konfiguration.initialisiere(db) == len(konfiguration.STANDARDWERTE)
    assert konfiguration.initialisiere(db) == 0


def test_lies_faellt_auf_standard_zurueck(db: Session) -> None:
    assert konfiguration.lies_int(db, "selbstverpflichtung_erinnerung_vorlauf_tage") == 60
    with pytest.raises(KeyError):
        konfiguration.lies(db, "gibt-es-nicht")


def test_setze_legt_an_und_aktualisiert(db: Session) -> None:
    konfiguration.setze(db, "asset_inaktiv_tage", "90")
    assert konfiguration.lies_int(db, "asset_inaktiv_tage") == 90
    konfiguration.setze(db, "asset_inaktiv_tage", "30")
    assert konfiguration.lies_int(db, "asset_inaktiv_tage") == 30


@pytest.mark.parametrize(("tier", "erwartet"), [(1, 90), (2, 30), (3, 14), (9, 14), (0, 90)])
def test_lenkungsfrist_je_tier(db: Session, tier: int, erwartet: int) -> None:
    assert konfiguration.lenkungsfrist_tage(db, tier) == erwartet


def test_governance_aendert_einstellung_im_betrieb(
    client: TestClient, governance, anmelden, db
) -> None:
    from app.models.audit import ChangeLog

    liste = client.get("/api/v1/konfiguration", headers=governance.kopf).json()
    assert any(e["schluessel"] == "lenkung_frist_tage_tier3" for e in liste)

    antwort = client.put(
        "/api/v1/konfiguration/lenkung_frist_tage_tier3",
        json={"wert": "7"},
        headers=governance.kopf,
    )
    assert antwort.status_code == 200
    assert antwort.json()["wert"] == "7"

    db.expire_all()
    eintrag = db.query(ChangeLog).filter(ChangeLog.entity_type == "konfiguration").one()
    assert eintrag.vorher["wert"] == "14"
    assert eintrag.nachher["wert"] == "7"


def test_nur_governance_aendert_einstellungen(client: TestClient, anmelden) -> None:
    fremder = anmelden("Ohne Rolle")
    antwort = client.put(
        "/api/v1/konfiguration/asset_inaktiv_tage", json={"wert": "1"}, headers=fremder.kopf
    )
    assert antwort.status_code == 403


def test_unbekannter_schluessel_liefert_404(client: TestClient, governance) -> None:
    antwort = client.put(
        "/api/v1/konfiguration/erfunden", json={"wert": "1"}, headers=governance.kopf
    )
    assert antwort.status_code == 404
