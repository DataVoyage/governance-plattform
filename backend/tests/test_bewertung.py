"""Bewertungs-Modul — Abnahmekriterien Phase 2 (Architektur 8.2)."""

from __future__ import annotations

import itertools

import pytest
from fastapi.testclient import TestClient

from app.services import bewertung as bewertung_service
from app.services.bewertungsbaum import BAUM, KI_VERBOTEN, Block

# --- Antwortmuster --------------------------------------------------------

#: Kein KI-Einsatz, sonst alles verneint — Profil 0-0-0-0-0-0.
ALLES_NEIN = {"1a": False, **{f.id: False for b in BAUM for f in b.fragen if f.id != "1a"}}


def antworten_fuer(profil: dict[str, int]) -> dict[str, bool]:
    """Baut das Antwortmuster, das genau zu diesem Profil fuehrt.

    Innerhalb eines Blocks steht die schwerste Frage vorn; die erste bejahte
    bestimmt die Stufe. Fuer Stufe n wird also genau die Frage bejaht, deren
    ``stufe_bei_ja`` gleich n ist, und alle davor verneint.
    """
    antworten: dict[str, bool] = {}
    for themenblock in BAUM:
        ziel = profil[themenblock.block.value]
        for frage in themenblock.fragen:
            if frage.id == "1a":
                antworten["1a"] = ziel != 0
                if ziel == 0:
                    break
                continue
            antworten[frage.id] = frage.stufe_bei_ja == ziel
            if frage.stufe_bei_ja == ziel:
                break
    return antworten


def profil_von(ki=0, ds=0, mb=0, it=0, rg=0, ur=0) -> dict[str, int]:
    return {"ki": ki, "ds": ds, "mb": mb, "it": it, "rg": rg, "ur": ur}


# --- Reihenfolge und Vollstaendigkeit des Baums ---------------------------


def test_bloecke_stehen_in_der_festgelegten_reihenfolge() -> None:
    """Abnahmekriterium 2.1: KI, DS, MB, IT, RG, UR — serverseitig fest."""
    assert [b.block for b in BAUM] == [
        Block.KI,
        Block.DS,
        Block.MB,
        Block.IT,
        Block.RG,
        Block.UR,
    ]


def test_wizard_fragt_die_bloecke_der_reihe_nach() -> None:
    antworten: dict[str, bool] = {}
    gesehen: list[str] = []
    while True:
        stand = bewertung_service.durchlaufe(antworten)
        if stand.naechste_frage is None:
            break
        gesehen.append(stand.naechste_frage.id)
        antworten[stand.naechste_frage.id] = False
    # Zuerst 1a; ein "nein" dort ueberspringt den Rest des KI-Blocks.
    assert gesehen[0] == "1a"
    assert [f[0] for f in gesehen] == sorted(f[0] for f in gesehen)
    assert "1b" not in gesehen


@pytest.mark.parametrize(
    "kombination",
    list(itertools.product([0, 1, 2, 3], repeat=6)),
)
def test_jede_antwortkombination_ergibt_das_tabellierte_tier(
    kombination: tuple[int, ...],
) -> None:
    """Abnahmekriterium 2.1: Verifikation ueber alle 4096 Kombinationen.

    Das tabellierte Tier ist die hoechste erreichte Stufe, mindestens 1.
    """
    profil = dict(zip(["ki", "ds", "mb", "it", "rg", "ur"], kombination, strict=True))
    stand = bewertung_service.durchlaufe(antworten_fuer(profil))
    assert stand.abgeschlossen
    assert bewertung_service.profil(stand) == profil
    assert bewertung_service.tier(stand) == max(1, max(kombination))


def test_ohne_ki_einsatz_bleibt_der_block_auf_null() -> None:
    stand = bewertung_service.durchlaufe(ALLES_NEIN)
    assert stand.abgeschlossen
    assert bewertung_service.profil(stand)["ki"] == 0
    assert bewertung_service.tier(stand) == 1


def test_ki_einsatz_ohne_weitere_treffer_ergibt_stufe_eins() -> None:
    antworten = dict(ALLES_NEIN)
    antworten["1a"] = True
    stand = bewertung_service.durchlaufe(antworten)
    assert bewertung_service.profil(stand)["ki"] == 1


def test_unbekannter_modus() -> None:
    from app.services.prozess import Ungueltig

    with pytest.raises(Ungueltig):
        bewertung_service.durchlaufe({}, "gemuetlich")


# --- Verbotstatbestand (Abnahmekriterium 2.2) ----------------------------


def test_verbotstatbestand_bricht_sofort_ab() -> None:
    stand = bewertung_service.durchlaufe({"1a": True, "1b": True})
    assert stand.verboten
    assert stand.abgeschlossen
    assert stand.stufen[Block.KI] == KI_VERBOTEN


# --- K-Klassen (Abnahmekriterium 2.5) ------------------------------------


def test_beispiel_aus_dem_leitdokument() -> None:
    """Profil KI0-DS3-MB1-IT1-RG2-UR2 loest K1-K5, K7, K8, K9 aus — nicht K6, nicht K10."""
    klassen = bewertung_service.leite_k_klassen_ab(profil_von(ds=3, mb=1, it=1, rg=2, ur=2))
    assert klassen == ["K1", "K2", "K3", "K4", "K5", "K7", "K8", "K9"]
    assert "K6" not in klassen
    assert "K10" not in klassen


@pytest.mark.parametrize(
    ("profil", "erwartet_enthalten", "erwartet_fehlend"),
    [
        (profil_von(), ["K1", "K2"], ["K3", "K4", "K5", "K6", "K7", "K8", "K9", "K10"]),
        (profil_von(ki=1), ["K6"], ["K10"]),
        (profil_von(ki=3), ["K6", "K10", "K3"], ["K4"]),
        (profil_von(it=2), ["K5", "K3"], ["K4", "K10"]),
        (profil_von(it=3), ["K5", "K10"], ["K4"]),
        (profil_von(ur=3), ["K9", "K10"], ["K4"]),
        (profil_von(ds=2), ["K5"], ["K4"]),
        (profil_von(mb=3), ["K7", "K3"], ["K10"]),
        (profil_von(rg=1), ["K1"], ["K8", "K3"]),
    ],
)
def test_k_klassen_je_ausloeser(
    profil: dict[str, int], erwartet_enthalten: list[str], erwartet_fehlend: list[str]
) -> None:
    klassen = set(bewertung_service.leite_k_klassen_ab(profil))
    assert set(erwartet_enthalten) <= klassen
    assert klassen.isdisjoint(erwartet_fehlend)


def test_jede_k_klasse_hat_eine_beschreibung() -> None:
    alle = set(bewertung_service.leite_k_klassen_ab(profil_von(3, 3, 3, 3, 3, 3)))
    assert alle == set(bewertung_service.K_KLASSEN_BESCHREIBUNG)


# --- Schnelle und vollstaendige Variante (Abnahmekriterium 2.3) ----------


def test_schnelle_variante_endet_beim_ersten_tier_3_treffer() -> None:
    antworten = antworten_fuer(profil_von(ds=3, rg=3))
    stand = bewertung_service.durchlaufe(antworten, bewertung_service.Modus.SCHNELL)
    assert stand.abgeschlossen
    assert not stand.vollstaendig
    # Nach dem Datenschutzblock ist Schluss; RG wurde nicht mehr gewertet.
    assert bewertung_service.profil(stand) == profil_von(ds=3)
    assert bewertung_service.tier(stand) == 3


def test_schnelle_variante_ohne_treffer_laeuft_durch() -> None:
    stand = bewertung_service.durchlaufe(
        antworten_fuer(profil_von(ds=2)), bewertung_service.Modus.SCHNELL
    )
    assert stand.abgeschlossen
    assert stand.vollstaendig
    assert bewertung_service.tier(stand) == 2


def test_vollstaendige_variante_liefert_das_ganze_profil() -> None:
    stand = bewertung_service.durchlaufe(antworten_fuer(profil_von(ds=3, rg=3)))
    assert stand.vollstaendig
    assert bewertung_service.profil(stand) == profil_von(ds=3, rg=3)


# --- HTTP-Schicht ---------------------------------------------------------


@pytest.fixture
def owner(anmelden, rolle_geben, organisation):
    nutzer = anmelden("Prozess-Owner", subject="sub-owner")
    rolle_geben(nutzer.user_id, "prozess_owner", "organisationseinheit", organisation["fin_int"])
    return nutzer


@pytest.fixture
def vertretung(anmelden):
    return anmelden("Stellvertretung", subject="sub-vertretung")


@pytest.fixture
def prozess(client: TestClient, owner, vertretung, prozess_daten):
    antwort = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    )
    assert antwort.status_code == 201, antwort.text
    return antwort.json()


def wizard(client: TestClient, anmeldung, prozess_id: str, antworten: dict, modus="vollstaendig"):
    return client.post(
        f"/api/v1/prozesse/{prozess_id}/bewertung/wizard",
        json={"modus": modus, "antworten": antworten},
        headers=anmeldung.kopf,
    )


def abschliessen(
    client: TestClient, anmeldung, prozess_id: str, antworten: dict, modus="vollstaendig"
):
    return client.post(
        f"/api/v1/prozesse/{prozess_id}/bewertungen",
        json={"modus": modus, "antworten": antworten},
        headers=anmeldung.kopf,
    )


def test_wizard_zeigt_keinen_zwischenstand(client: TestClient, owner, prozess) -> None:
    """Architektur 8.2: das Ergebnis erscheint erst am Ende."""
    antwort = wizard(client, owner, prozess["id"], {"1a": False, "2a": True})
    koerper = antwort.json()
    assert antwort.status_code == 200
    assert koerper["abgeschlossen"] is False
    assert koerper["vorschau"] is None
    assert koerper["naechste_frage"]["id"] == "3a"
    assert koerper["naechste_frage"]["block"] == "mb"
    assert koerper["naechste_frage"]["nummer"] == 3
    assert koerper["naechste_frage"]["anzahl_bloecke"] == 6


def test_wizard_liefert_am_ende_die_vorschau(client: TestClient, owner, prozess) -> None:
    antwort = wizard(
        client, owner, prozess["id"], antworten_fuer(profil_von(ds=3, mb=1, it=1, rg=2, ur=2))
    )
    koerper = antwort.json()
    assert koerper["abgeschlossen"] is True
    assert koerper["vorschau"]["tier"] == 3
    assert koerper["vorschau"]["ausgeloeste_k_klassen"] == [
        "K1",
        "K2",
        "K3",
        "K4",
        "K5",
        "K7",
        "K8",
        "K9",
    ]


def test_wizard_meldet_verbot_ohne_vorschau(client: TestClient, owner, prozess) -> None:
    koerper = wizard(client, owner, prozess["id"], {"1a": True, "1b": True}).json()
    assert koerper["verboten"] is True
    assert koerper["vorschau"] is None


def test_wizard_lehnt_unbekannte_frage_ab(client: TestClient, owner, prozess) -> None:
    antwort = wizard(client, owner, prozess["id"], {"9z": True})
    assert antwort.status_code == 422


def test_wizard_lehnt_unbekannten_modus_ab(client: TestClient, owner, prozess) -> None:
    antwort = client.post(
        f"/api/v1/prozesse/{prozess['id']}/bewertung/wizard",
        json={"modus": "gemuetlich", "antworten": {}},
        headers=owner.kopf,
    )
    assert antwort.status_code == 422


def test_bewertung_speichern_und_profil_lesen(client: TestClient, owner, prozess, db) -> None:
    antwort = abschliessen(
        client, owner, prozess["id"], antworten_fuer(profil_von(ds=3, mb=1, it=1, rg=2, ur=2))
    )
    assert antwort.status_code == 201, antwort.text
    bewertung = antwort.json()["bewertung"]
    assert antwort.json()["alarm"] is None
    assert bewertung["tier"] == 3
    assert bewertung["ds_stufe"] == 3
    assert bewertung["mb_stufe"] == 1
    assert bewertung["vollstaendig"] is True
    # Ab Tier 3 gilt die jaehrliche Erneuerungspflicht.
    assert bewertung["gueltig_bis"] is not None

    detail = client.get(f"/api/v1/prozesse/{prozess['id']}", headers=owner.kopf).json()
    assert detail["tier"] == 3
    assert "K4" in detail["ausgeloeste_k_klassen"]
    # Die Mitbestimmungsstufe schlaegt auf das abgeleitete Flag durch.
    assert detail["mitbestimmung_flag"] is True


def test_tier_1_und_2_haben_keine_erneuerungsfrist(client: TestClient, owner, prozess) -> None:
    antwort = abschliessen(client, owner, prozess["id"], antworten_fuer(profil_von(ds=2)))
    assert antwort.json()["bewertung"]["gueltig_bis"] is None


def test_unvollstaendiger_durchlauf_wird_abgelehnt(client: TestClient, owner, prozess) -> None:
    antwort = abschliessen(client, owner, prozess["id"], {"1a": False})
    assert antwort.status_code == 422
    assert "2a" in antwort.json()["detail"]


def test_schnelle_variante_speichert_ohne_k_klassen(client: TestClient, owner, prozess) -> None:
    """Ohne vollstaendigen Durchlauf gibt es kein belastbares K-Klassen-Bild."""
    antwort = abschliessen(
        client, owner, prozess["id"], antworten_fuer(profil_von(ds=3)), modus="schnell"
    )
    bewertung = antwort.json()["bewertung"]
    assert bewertung["tier"] == 3
    assert bewertung["vollstaendig"] is False
    assert bewertung["ausgeloeste_k_klassen"] == []


def test_verbotstatbestand_speichert_keine_bewertung(
    client: TestClient, owner, prozess, db
) -> None:
    """Abnahmekriterium 2.2: kein Datensatz, stattdessen ein Alarm."""
    from app.models.governance import Alarm, Bewertung

    antwort = abschliessen(client, owner, prozess["id"], {"1a": True, "1b": True})
    assert antwort.status_code == 201
    assert antwort.json()["bewertung"] is None
    assert antwort.json()["alarm"]["typ"] == "ki_verbotstatbestand"

    db.expire_all()
    assert db.query(Bewertung).count() == 0
    alarm = db.query(Alarm).one()
    assert alarm.prozessobjekt_id is not None
    assert (
        client.get(f"/api/v1/prozesse/{prozess['id']}", headers=owner.kopf).json()["tier"] is None
    )


def test_neubewertung_erzeugt_neuen_datensatz(client: TestClient, owner, prozess) -> None:
    """Abnahmekriterium 2.4: die vorherige Bewertung bleibt einsehbar."""
    erste = abschliessen(client, owner, prozess["id"], antworten_fuer(profil_von(ds=1))).json()[
        "bewertung"
    ]
    zweite = abschliessen(client, owner, prozess["id"], antworten_fuer(profil_von(ds=3))).json()[
        "bewertung"
    ]
    assert erste["id"] != zweite["id"]

    historie = client.get(
        f"/api/v1/prozesse/{prozess['id']}/bewertungen", headers=owner.kopf
    ).json()
    assert [b["id"] for b in historie] == [zweite["id"], erste["id"]]
    assert historie[1]["ds_stufe"] == 1
    assert historie[1]["tier"] == 1


def test_bewertung_landet_im_nachweis(client: TestClient, owner, prozess, db) -> None:
    from app.models.audit import ChangeLog

    abschliessen(client, owner, prozess["id"], antworten_fuer(profil_von(ds=2)))
    db.expire_all()
    assert db.query(ChangeLog).filter(ChangeLog.entity_type == "bewertungen").count() == 1


def test_nur_der_prozess_owner_darf_bewerten(
    client: TestClient, prozess, anmelden, rolle_geben, organisation
) -> None:
    umsetzer = anmelden("Umsetzer DE")
    rolle_geben(
        umsetzer.user_id, "prozess_umsetzer", "organisationseinheit", organisation["fin_de"]
    )
    antwort = abschliessen(client, umsetzer, prozess["id"], antworten_fuer(profil_von(ds=1)))
    assert antwort.status_code in (403,)


def test_auditor_darf_lesen_aber_nicht_bewerten(
    client: TestClient, owner, prozess, anmelden, rolle_geben
) -> None:
    abschliessen(client, owner, prozess["id"], antworten_fuer(profil_von(ds=2)))
    auditor = anmelden("Auditor")
    rolle_geben(auditor.user_id, "auditor", "global")
    assert (
        client.get(
            f"/api/v1/prozesse/{prozess['id']}/bewertungen", headers=auditor.kopf
        ).status_code
        == 200
    )
    assert (
        abschliessen(client, auditor, prozess["id"], antworten_fuer(profil_von(ds=1))).status_code
        == 403
    )


def test_governance_darf_bewerten(client: TestClient, prozess, anmelden, rolle_geben) -> None:
    governance = anmelden("Governance")
    rolle_geben(governance.user_id, "governance", "global")
    antwort = abschliessen(client, governance, prozess["id"], antworten_fuer(profil_von(rg=3)))
    assert antwort.status_code == 201


def test_bewertung_eines_fremden_prozesses_ist_nicht_sichtbar(
    client: TestClient, prozess, anmelden
) -> None:
    fremder = anmelden("Ohne Rolle")
    assert (
        client.get(
            f"/api/v1/prozesse/{prozess['id']}/bewertungen", headers=fremder.kopf
        ).status_code
        == 403
    )


# --- Gueltigkeit ----------------------------------------------------------


def test_ablauf_wird_erkannt(db, client: TestClient, owner, prozess) -> None:
    from datetime import UTC, datetime, timedelta

    abschliessen(client, owner, prozess["id"], antworten_fuer(profil_von(ds=3)))
    db.expire_all()
    aktuelle = bewertung_service.aktuelle(db, __import__("uuid").UUID(prozess["id"]))
    assert aktuelle is not None
    assert not bewertung_service.ist_abgelaufen(aktuelle)
    assert bewertung_service.ist_abgelaufen(aktuelle, datetime.now(UTC) + timedelta(days=400))


def test_ohne_frist_laeuft_nichts_ab(db, client: TestClient, owner, prozess) -> None:
    import uuid as uuid_modul

    abschliessen(client, owner, prozess["id"], antworten_fuer(profil_von(ds=1)))
    db.expire_all()
    aktuelle = bewertung_service.aktuelle(db, uuid_modul.UUID(prozess["id"]))
    assert aktuelle is not None
    assert not bewertung_service.ist_abgelaufen(aktuelle)


def test_ohne_bewertung_gibt_es_keine_aktuelle(db, prozess) -> None:
    import uuid as uuid_modul

    assert bewertung_service.aktuelle(db, uuid_modul.UUID(prozess["id"])) is None
