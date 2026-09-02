"""Prozess-Modul — Abnahmekriterien Phase 1.3 bis 1.5."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def owner(client: TestClient, anmelden, rolle_geben, organisation):
    """Prozess-Owner mit Scope auf der INT-Einheit von Finance."""
    nutzer = anmelden("Prozess-Owner Finance", subject="sub-owner")
    rolle_geben(nutzer.user_id, "prozess_owner", "organisationseinheit", organisation["fin_int"])
    return nutzer


@pytest.fixture
def vertretung(anmelden):
    return anmelden("Stellvertretung", subject="sub-vertretung")


@pytest.fixture
def governance(anmelden, rolle_geben):
    nutzer = anmelden("Governance", subject="sub-governance")
    rolle_geben(nutzer.user_id, "governance", "global")
    return nutzer


def anlegen(client: TestClient, anmeldung, daten: dict):
    return client.post("/api/v1/prozesse", json=daten, headers=anmeldung.kopf)


def aktiviere(client: TestClient, anmeldung, prozess_id: str):
    """Bewertet mit Tier 1 und setzt den Prozess aktiv.

    Ab Tier 3 kaemen Selbstverpflichtung und Gate 1 dazu (siehe test_gates.py);
    fuer die Sichtbarkeits- und Filtertests genuegt der einfache Weg.
    """
    from tests.test_bewertung import nutzlast, profil_von

    client.post(
        f"/api/v1/prozesse/{prozess_id}/bewertungen",
        json=nutzlast(profil_von(ur=1)),
        headers=anmeldung.kopf,
    )
    antwort = client.patch(
        f"/api/v1/prozesse/{prozess_id}", json={"status": "aktiv"}, headers=anmeldung.kopf
    )
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def test_owner_legt_prozess_mit_allen_zehn_feldern_an(
    client: TestClient, owner, vertretung, prozess_daten
) -> None:
    antwort = anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id))
    assert antwort.status_code == 201, antwort.text
    prozess = antwort.json()
    assert prozess["name"] == "Rechnungspruefung"
    assert prozess["status"] == "entwurf"
    # Abgeleitete Felder erscheinen, ohne dass sie eingegeben wurden.
    assert prozess["reichweite"] == "bereich"
    assert prozess["kritikalitaet"] == 2
    assert prozess["mitbestimmung_flag"] is False


@pytest.mark.parametrize(
    "feld",
    [
        "name",
        "owner_user_id",
        "stellvertretung_user_id",
        "prozessgeber_org_id",
        "customer",
        "ausfallfolge",
    ],
)
def test_pflichtfelder_fehlen(
    client: TestClient, owner, vertretung, prozess_daten, feld: str
) -> None:
    daten = prozess_daten(owner.user_id, vertretung.user_id)
    daten.pop(feld)
    assert anlegen(client, owner, daten).status_code == 422


def test_speichern_ohne_stellvertretung_wird_abgelehnt(
    client: TestClient, owner, vertretung, prozess_daten
) -> None:
    """Abnahmekriterium 1.3: kein Speichern ohne Stellvertretung."""
    daten = prozess_daten(owner.user_id, vertretung.user_id)
    daten["stellvertretung_user_id"] = None
    assert anlegen(client, owner, daten).status_code == 422


def test_abgeleitete_felder_sind_nicht_eingebbar(
    client: TestClient, owner, vertretung, prozess_daten
) -> None:
    """Reichweite und Kritikalitaet werden berechnet, nicht entgegengenommen."""
    daten = prozess_daten(owner.user_id, vertretung.user_id)
    daten["reichweite"] = "extern"
    daten["kritikalitaet"] = 3
    antwort = anlegen(client, owner, daten)
    assert antwort.status_code == 201
    assert antwort.json()["reichweite"] == "bereich"
    assert antwort.json()["kritikalitaet"] == 2


def test_prozessgeber_muss_int_ebene_sein(
    client: TestClient, owner, vertretung, prozess_daten, organisation
) -> None:
    daten = prozess_daten(
        owner.user_id, vertretung.user_id, prozessgeber_org_id=organisation["fin_de"]
    )
    antwort = anlegen(client, owner, daten)
    assert antwort.status_code == 422


def test_unbekannter_prozessgeber(client: TestClient, owner, vertretung, prozess_daten) -> None:
    daten = prozess_daten(
        owner.user_id,
        vertretung.user_id,
        prozessgeber_org_id="00000000-0000-0000-0000-000000000000",
    )
    assert anlegen(client, owner, daten).status_code == 422


def test_ohne_rolle_kein_anlegen_und_kein_aendern(
    client: TestClient, owner, vertretung, prozess_daten, anmelden
) -> None:
    """Abnahmekriterium 1.4: ohne Rollenzuweisung im Scope kein Schreibzugriff."""
    fremder = anmelden("Ohne Rolle")
    assert (
        anlegen(client, fremder, prozess_daten(owner.user_id, vertretung.user_id)).status_code
        == 403
    )

    prozess = anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id)).json()
    antwort = client.patch(
        f"/api/v1/prozesse/{prozess['id']}", json={"name": "Umbenannt"}, headers=fremder.kopf
    )
    assert antwort.status_code == 403


def test_owner_eines_anderen_fachbereichs_darf_nicht_schreiben(
    client: TestClient, owner, vertretung, prozess_daten, anmelden, rolle_geben, organisation
) -> None:
    hr_owner = anmelden("HR-Owner")
    rolle_geben(hr_owner.user_id, "prozess_owner", "organisationseinheit", organisation["hr_int"])
    assert (
        anlegen(client, hr_owner, prozess_daten(owner.user_id, vertretung.user_id)).status_code
        == 403
    )


def test_fachbereichsscope_deckt_die_int_einheit_ab(
    client: TestClient, vertretung, prozess_daten, anmelden, rolle_geben, organisation
) -> None:
    nutzer = anmelden("Owner mit Fachbereichsscope")
    rolle_geben(nutzer.user_id, "prozess_owner", "fachbereich", organisation["fachbereich_finance"])
    antwort = anlegen(client, nutzer, prozess_daten(nutzer.user_id, vertretung.user_id))
    assert antwort.status_code == 201


def test_governance_darf_ueberall_schreiben(
    client: TestClient, governance, vertretung, prozess_daten
) -> None:
    antwort = anlegen(client, governance, prozess_daten(governance.user_id, vertretung.user_id))
    assert antwort.status_code == 201


def test_prozess_aendern_und_status_setzen(
    client: TestClient, owner, vertretung, prozess_daten
) -> None:
    prozess = anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id)).json()
    antwort = client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"name": "Rechnungspruefung DE", "ausfallfolge": "kritisch"},
        headers=owner.kopf,
    )
    assert antwort.status_code == 200
    assert antwort.json()["name"] == "Rechnungspruefung DE"
    assert antwort.json()["kritikalitaet"] == 3
    # Der Statuswechsel nach "aktiv" hat eigene Bedingungen; siehe test_gates.py.
    assert antwort.json()["status"] == "entwurf"


def test_prozessgeber_wechsel_nur_in_den_eigenen_bereich(
    client: TestClient, owner, vertretung, prozess_daten, organisation
) -> None:
    prozess = anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id)).json()
    antwort = client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"prozessgeber_org_id": organisation["hr_int"]},
        headers=owner.kopf,
    )
    assert antwort.status_code == 403


def test_prozessgeber_wechsel_auf_land_einheit_abgelehnt(
    client: TestClient, governance, vertretung, prozess_daten, organisation
) -> None:
    prozess = anlegen(
        client, governance, prozess_daten(governance.user_id, vertretung.user_id)
    ).json()
    antwort = client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"prozessgeber_org_id": organisation["fin_de"]},
        headers=governance.kopf,
    )
    assert antwort.status_code == 422


def test_unbekannter_prozess_liefert_404(client: TestClient, owner) -> None:
    antwort = client.get(
        "/api/v1/prozesse/00000000-0000-0000-0000-000000000000", headers=owner.kopf
    )
    assert antwort.status_code == 404


# --- n:m-Umsetzungen (Abnahmekriterium 1.5) ------------------------------


def test_prozess_in_zwei_laendern_umsetzen(
    client: TestClient, owner, vertretung, prozess_daten, organisation
) -> None:
    daten = prozess_daten(
        owner.user_id,
        vertretung.user_id,
        umsetzung_land_org_ids=[organisation["fin_de"], organisation["fin_fr"]],
    )
    prozess = anlegen(client, owner, daten).json()
    assert len(prozess["umsetzungen"]) == 2
    # Mehr als eine Umsetzung hebt die Reichweite auf unternehmensweit an.
    assert prozess["reichweite"] == "unternehmen"


def test_umsetzung_nachtraeglich_anlegen_und_entfernen(
    client: TestClient, owner, vertretung, prozess_daten, organisation
) -> None:
    prozess = anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id)).json()
    angelegt = client.post(
        f"/api/v1/prozesse/{prozess['id']}/umsetzungen",
        json={"land_org_id": organisation["fin_de"], "lokale_abweichung": "Vier-Augen-Prinzip"},
        headers=owner.kopf,
    )
    assert angelegt.status_code == 201
    doppelt = client.post(
        f"/api/v1/prozesse/{prozess['id']}/umsetzungen",
        json={"land_org_id": organisation["fin_de"]},
        headers=owner.kopf,
    )
    assert doppelt.status_code == 422
    entfernt = client.delete(
        f"/api/v1/prozesse/{prozess['id']}/umsetzungen/{angelegt.json()['id']}",
        headers=owner.kopf,
    )
    assert entfernt.status_code == 204
    assert (
        client.get(f"/api/v1/prozesse/{prozess['id']}", headers=owner.kopf).json()["umsetzungen"]
        == []
    )


def test_umsetzung_verlangt_land_einheit(
    client: TestClient, owner, vertretung, prozess_daten, organisation
) -> None:
    prozess = anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id)).json()
    antwort = client.post(
        f"/api/v1/prozesse/{prozess['id']}/umsetzungen",
        json={"land_org_id": organisation["hr_int"]},
        headers=owner.kopf,
    )
    assert antwort.status_code == 422


def test_umsetzung_mit_unbekannter_einheit(
    client: TestClient, owner, vertretung, prozess_daten
) -> None:
    prozess = anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id)).json()
    antwort = client.post(
        f"/api/v1/prozesse/{prozess['id']}/umsetzungen",
        json={"land_org_id": "00000000-0000-0000-0000-000000000000"},
        headers=owner.kopf,
    )
    assert antwort.status_code == 422


def test_umsetzer_pflegt_nur_die_lokale_abweichung(
    client: TestClient, owner, vertretung, prozess_daten, anmelden, rolle_geben, organisation
) -> None:
    """Matrix 5.3: der Prozess-Umsetzer aendert die lokale Abweichung, sonst nichts."""
    daten = prozess_daten(
        owner.user_id, vertretung.user_id, umsetzung_land_org_ids=[organisation["fin_de"]]
    )
    prozess = anlegen(client, owner, daten).json()
    umsetzung_id = prozess["umsetzungen"][0]["id"]

    umsetzer = anmelden("Umsetzer DE")
    rolle_geben(
        umsetzer.user_id, "prozess_umsetzer", "organisationseinheit", organisation["fin_de"]
    )

    geaendert = client.patch(
        f"/api/v1/prozesse/{prozess['id']}/umsetzungen/{umsetzung_id}",
        json={"lokale_abweichung": "Lokale Freigabegrenze 5.000 EUR"},
        headers=umsetzer.kopf,
    )
    assert geaendert.status_code == 200
    assert geaendert.json()["lokale_abweichung"] == "Lokale Freigabegrenze 5.000 EUR"

    verweigert = client.patch(
        f"/api/v1/prozesse/{prozess['id']}", json={"name": "Neu"}, headers=umsetzer.kopf
    )
    assert verweigert.status_code == 403
    entfernen = client.delete(
        f"/api/v1/prozesse/{prozess['id']}/umsetzungen/{umsetzung_id}", headers=umsetzer.kopf
    )
    assert entfernen.status_code == 403


def test_umsetzer_fremder_laender_darf_nicht(
    client: TestClient, owner, vertretung, prozess_daten, anmelden, rolle_geben, organisation
) -> None:
    daten = prozess_daten(
        owner.user_id, vertretung.user_id, umsetzung_land_org_ids=[organisation["fin_de"]]
    )
    prozess = anlegen(client, owner, daten).json()
    umsetzung_id = prozess["umsetzungen"][0]["id"]
    fr_umsetzer = anmelden("Umsetzer FR")
    rolle_geben(
        fr_umsetzer.user_id, "prozess_umsetzer", "organisationseinheit", organisation["fin_fr"]
    )
    antwort = client.patch(
        f"/api/v1/prozesse/{prozess['id']}/umsetzungen/{umsetzung_id}",
        json={"lokale_abweichung": "Fremd"},
        headers=fr_umsetzer.kopf,
    )
    assert antwort.status_code == 403


def test_unbekannte_umsetzung_liefert_404(
    client: TestClient, owner, vertretung, prozess_daten
) -> None:
    prozess = anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id)).json()
    antwort = client.patch(
        f"/api/v1/prozesse/{prozess['id']}/umsetzungen/00000000-0000-0000-0000-000000000000",
        json={"lokale_abweichung": "x"},
        headers=owner.kopf,
    )
    assert antwort.status_code == 404


# --- Sichtbarkeit (Architektur 4.3) --------------------------------------


def test_land_scope_sieht_nur_eigene_umsetzungen(
    client: TestClient, owner, vertretung, prozess_daten, anmelden, rolle_geben, organisation
) -> None:
    anlegen(
        client,
        owner,
        prozess_daten(
            owner.user_id,
            vertretung.user_id,
            name="Nur DE",
            umsetzung_land_org_ids=[organisation["fin_de"]],
        ),
    )
    anlegen(
        client,
        owner,
        prozess_daten(
            owner.user_id,
            vertretung.user_id,
            name="Nur FR",
            umsetzung_land_org_ids=[organisation["fin_fr"]],
        ),
    )
    de_nutzer = anmelden("Sicht DE")
    rolle_geben(
        de_nutzer.user_id, "prozess_umsetzer", "organisationseinheit", organisation["fin_de"]
    )
    sichtbar = client.get("/api/v1/prozesse", headers=de_nutzer.kopf).json()
    assert [p["name"] for p in sichtbar] == ["Nur DE"]


def test_auditor_sieht_global_und_darf_nicht_schreiben(
    client: TestClient, owner, vertretung, prozess_daten, anmelden, rolle_geben
) -> None:
    prozess = anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id)).json()
    auditor = anmelden("Auditor")
    rolle_geben(auditor.user_id, "auditor", "global")
    assert len(client.get("/api/v1/prozesse", headers=auditor.kopf).json()) == 1
    assert client.get(f"/api/v1/prozesse/{prozess['id']}", headers=auditor.kopf).status_code == 200
    antwort = client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"name": "Auditor-Aenderung"},
        headers=auditor.kopf,
    )
    assert antwort.status_code == 403


def test_nutzer_ohne_rolle_sieht_nichts(
    client: TestClient, owner, vertretung, prozess_daten, anmelden
) -> None:
    prozess = anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id)).json()
    fremder = anmelden("Ohne Rolle")
    assert client.get("/api/v1/prozesse", headers=fremder.kopf).json() == []
    assert client.get(f"/api/v1/prozesse/{prozess['id']}", headers=fremder.kopf).status_code == 403


def test_stellvertretung_sieht_den_eigenen_prozess(
    client: TestClient, owner, vertretung, prozess_daten
) -> None:
    anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id))
    sichtbar = client.get("/api/v1/prozesse", headers=vertretung.kopf).json()
    assert len(sichtbar) == 1


def test_liste_nach_fachbereich_und_status_filtern(
    client: TestClient, owner, vertretung, prozess_daten, organisation, governance
) -> None:
    erster = anlegen(
        client, owner, prozess_daten(owner.user_id, vertretung.user_id, name="Aktiv")
    ).json()
    anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id, name="Entwurf"))
    aktiviere(client, owner, erster["id"])
    nur_aktiv = client.get("/api/v1/prozesse?status_filter=aktiv", headers=governance.kopf).json()
    assert [p["name"] for p in nur_aktiv] == ["Aktiv"]
    finance = client.get(
        f"/api/v1/prozesse?fachbereich_id={organisation['fachbereich_finance']}",
        headers=governance.kopf,
    ).json()
    assert len(finance) == 2
    hr = client.get(
        f"/api/v1/prozesse?fachbereich_id={organisation['fachbereich_hr']}",
        headers=governance.kopf,
    ).json()
    assert hr == []


# --- Prozesskette --------------------------------------------------------


def test_kritikalitaet_wird_entlang_der_kette_vererbt(
    client: TestClient, owner, vertretung, prozess_daten
) -> None:
    """Leitdokument A.4.2: wer einen kritischen Nachfolger speist, ist selbst kritisch."""
    nachfolger = anlegen(
        client,
        owner,
        prozess_daten(
            owner.user_id, vertretung.user_id, name="Zahlungslauf", ausfallfolge="kritisch"
        ),
    ).json()
    vorgaenger = anlegen(
        client,
        owner,
        prozess_daten(
            owner.user_id,
            vertretung.user_id,
            name="Rechnungserfassung",
            ausfallfolge="gering",
            nachgelagert_ids=[nachfolger["id"]],
        ),
    ).json()
    assert vorgaenger["kritikalitaet"] == 3
    assert vorgaenger["nachgelagert_ids"] == [nachfolger["id"]]


def test_kritikalitaet_wird_nachgefuehrt(
    client: TestClient, owner, vertretung, prozess_daten
) -> None:
    nachfolger = anlegen(
        client,
        owner,
        prozess_daten(owner.user_id, vertretung.user_id, name="Folge", ausfallfolge="keine"),
    ).json()
    vorgaenger = anlegen(
        client,
        owner,
        prozess_daten(
            owner.user_id,
            vertretung.user_id,
            name="Quelle",
            ausfallfolge="gering",
            nachgelagert_ids=[nachfolger["id"]],
        ),
    ).json()
    assert vorgaenger["kritikalitaet"] == 1
    client.patch(
        f"/api/v1/prozesse/{nachfolger['id']}",
        json={"ausfallfolge": "kritisch"},
        headers=owner.kopf,
    )
    aktualisiert = client.get(f"/api/v1/prozesse/{vorgaenger['id']}", headers=owner.kopf).json()
    assert aktualisiert["kritikalitaet"] == 3


def test_unbekannter_kettenverweis(client: TestClient, owner, vertretung, prozess_daten) -> None:
    daten = prozess_daten(
        owner.user_id,
        vertretung.user_id,
        vorgelagert_ids=["00000000-0000-0000-0000-000000000000"],
    )
    assert anlegen(client, owner, daten).status_code == 422


def test_unbekanntes_input_datenobjekt(
    client: TestClient, owner, vertretung, prozess_daten
) -> None:
    daten = prozess_daten(
        owner.user_id,
        vertretung.user_id,
        input_datenobjekt_ids=["00000000-0000-0000-0000-000000000000"],
    )
    assert anlegen(client, owner, daten).status_code == 422


# --- Umsetzungsplan AP-1: Schreibkante, Kette und Flughoehe ---------------


def _datenobjekt(client: TestClient, anmeldung, name: str) -> dict:
    antwort = client.post(
        "/api/v1/datenobjekte", json={"name": name, "beschreibung": ""}, headers=anmeldung.kopf
    )
    assert antwort.status_code == 201, antwort.text
    return antwort.json()


def test_output_datenobjekte_sind_referenzierbar(
    client: TestClient, owner, governance, vertretung, prozess_daten
) -> None:
    """Die Schreibkante des SIPOC (Leitdokument A.4.1) ist erfassbar.

    Ohne sie liesse sich nicht beantworten, wer in ein Datenobjekt schreibt —
    die Aufwaertsanalyse aus A.4.3 und der Erlaubnisrahmen aus A.13.2 haengen
    daran.
    """
    eingang = _datenobjekt(client, governance, "Kreditorenstamm")
    ergebnis = _datenobjekt(client, governance, "Buchungsjournal")

    antwort = anlegen(
        client,
        owner,
        prozess_daten(
            owner.user_id,
            vertretung.user_id,
            input_datenobjekt_ids=[eingang["id"]],
            output_datenobjekt_ids=[ergebnis["id"]],
        ),
    )
    assert antwort.status_code == 201, antwort.text
    prozess = antwort.json()
    assert prozess["input_datenobjekt_ids"] == [eingang["id"]]
    assert prozess["output_datenobjekt_ids"] == [ergebnis["id"]]


def test_output_datenobjekte_sind_aenderbar(
    client: TestClient, owner, governance, vertretung, prozess_daten
) -> None:
    ergebnis = _datenobjekt(client, governance, "Zahlungsvorschlag")
    prozess = anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id)).json()

    antwort = client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"output_datenobjekt_ids": [ergebnis["id"]]},
        headers=owner.kopf,
    )
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["output_datenobjekt_ids"] == [ergebnis["id"]]

    geleert = client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"output_datenobjekt_ids": []},
        headers=owner.kopf,
    )
    assert geleert.json()["output_datenobjekt_ids"] == []


def test_kette_bleibt_zyklenfrei(client: TestClient, owner, vertretung, prozess_daten) -> None:
    """Ein Kreis in der Prozesskette wird abgelehnt (Leitdokument A.4.2)."""
    erster = anlegen(
        client, owner, prozess_daten(owner.user_id, vertretung.user_id, name="Erster")
    ).json()
    zweiter = anlegen(
        client,
        owner,
        prozess_daten(
            owner.user_id, vertretung.user_id, name="Zweiter", vorgelagert_ids=[erster["id"]]
        ),
    ).json()

    # Zweiter liefert bereits an Erster zurueck zu machen schliesst den Kreis.
    antwort = client.patch(
        f"/api/v1/prozesse/{erster['id']}",
        json={"vorgelagert_ids": [zweiter["id"]]},
        headers=owner.kopf,
    )
    assert antwort.status_code == 422, antwort.text
    assert "Kreis" in antwort.json()["detail"]


def test_prozess_kann_sich_nicht_selbst_beliefern(
    client: TestClient, owner, vertretung, prozess_daten
) -> None:
    prozess = anlegen(client, owner, prozess_daten(owner.user_id, vertretung.user_id)).json()
    antwort = client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"nachgelagert_ids": [prozess["id"]]},
        headers=owner.kopf,
    )
    assert antwort.status_code == 422, antwort.text


def test_flughoehenwarnung_ab_acht_schritten(
    client: TestClient, owner, vertretung, prozess_daten
) -> None:
    """Mehr als sieben Schritte sind eine Warnung, keine Ablehnung (A.5)."""
    sieben = anlegen(
        client,
        owner,
        prozess_daten(
            owner.user_id,
            vertretung.user_id,
            process_steps="\n".join(f"Schritt {n}" for n in range(1, 8)),
        ),
    ).json()
    assert sieben["schritt_anzahl"] == 7
    assert sieben["schritte_zu_viele"] is False

    antwort = client.patch(
        f"/api/v1/prozesse/{sieben['id']}",
        json={"process_steps": "; ".join(f"Schritt {n}" for n in range(1, 10))},
        headers=owner.kopf,
    )
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["schritt_anzahl"] == 9
    assert antwort.json()["schritte_zu_viele"] is True


def test_freitextfelder_haben_harte_grenzen(
    client: TestClient, owner, vertretung, prozess_daten
) -> None:
    antwort = anlegen(
        client, owner, prozess_daten(owner.user_id, vertretung.user_id, supplier="x" * 201)
    )
    assert antwort.status_code == 422, antwort.text
