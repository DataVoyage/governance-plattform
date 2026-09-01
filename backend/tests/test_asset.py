"""Asset-Management — Abnahmekriterien Phase 3 (Architektur 8.3)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

QUELLE = "zentrale-entwicklungsplattform"


@pytest.fixture
def governance(anmelden, rolle_geben):
    nutzer = anmelden("Governance", subject="sub-gov")
    rolle_geben(nutzer.user_id, "governance", "global")
    return nutzer


@pytest.fixture
def plattform(anmelden, rolle_geben):
    nutzer = anmelden("Plattform", subject="sub-plattform")
    rolle_geben(nutzer.user_id, "plattform", "global")
    return nutzer


@pytest.fixture
def owner(anmelden, rolle_geben, organisation):
    nutzer = anmelden("Prozess-Owner", subject="sub-owner")
    rolle_geben(nutzer.user_id, "prozess_owner", "organisationseinheit", organisation["fin_int"])
    return nutzer


@pytest.fixture
def techniker(anmelden, rolle_geben, organisation):
    nutzer = anmelden("Technischer Owner", subject="sub-technik")
    rolle_geben(
        nutzer.user_id, "technischer_owner", "organisationseinheit", organisation["fin_de"]
    )
    return nutzer


@pytest.fixture
def vertretung(anmelden):
    return anmelden("Stellvertretung", subject="sub-vertretung")


def lege_prozess_an(client: TestClient, owner, vertretung, prozess_daten, **overrides):
    antwort = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id, **overrides),
        headers=owner.kopf,
    )
    assert antwort.status_code == 201, antwort.text
    return antwort.json()


def importiere(client: TestClient, plattform, datensaetze, quelle: str = QUELLE):
    antwort = client.post(
        "/api/v1/import/assets",
        json={"quelle": quelle, "datensaetze": datensaetze},
        headers=plattform.kopf,
    )
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


# --- Import von Tools und Datenobjekten (Abnahmekriterium 3.1, 3.2) ------


def test_importiertes_tool_ist_unbestaetigt_und_nicht_verknuepfbar(
    client: TestClient, plattform, governance, owner, vertretung, prozess_daten
) -> None:
    """Abnahmekriterium 3.1."""
    importiere(
        client,
        plattform,
        [
            {
                "typ": "tool",
                "externe_id": "TOOL-1",
                "name": "Rechnungs-Skript",
                "metadaten": {"technologie": "apps-script", "beschreibung": "Import"},
            }
        ],
    )
    tools = client.get("/api/v1/tools", headers=governance.kopf).json()
    assert len(tools) == 1
    tool = tools[0]
    assert tool["status"] == "importiert_unbestaetigt"
    assert tool["herkunft"] == "importiert"
    assert tool["technologie"] == "apps-script"

    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    verweigert = client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    assert verweigert.status_code == 422
    assert "bestaetigt" in verweigert.json()["detail"]

    bestaetigt = client.post(
        f"/api/v1/tools/{tool['id']}/bestaetigung", headers=governance.kopf
    )
    assert bestaetigt.status_code == 200
    assert bestaetigt.json()["status"] == "bestaetigt"

    verknuepft = client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    assert verknuepft.status_code == 201
    assert verknuepft.json()["prozessobjekt_ids"] == [prozess["id"]]


def test_zweiter_import_laesst_die_kategorie_unberuehrt(
    client: TestClient, plattform, governance
) -> None:
    """Abnahmekriterium 3.2: Governance-Felder ueberlebt der Sync."""
    importiere(
        client,
        plattform,
        [
            {
                "typ": "tool",
                "externe_id": "TOOL-2",
                "name": "Alter Name",
                "metadaten": {"technologie": "python", "umgebung": "alt"},
            }
        ],
    )
    tool_id = client.get("/api/v1/tools", headers=governance.kopf).json()[0]["id"]
    client.patch(
        f"/api/v1/tools/{tool_id}",
        json={"kategorie": "kernanwendung"},
        headers=governance.kopf,
    )

    importiere(
        client,
        plattform,
        [
            {
                "typ": "tool",
                "externe_id": "TOOL-2",
                "name": "Neuer Name",
                "metadaten": {"technologie": "python", "umgebung": "neu"},
            }
        ],
    )
    tool = client.get(f"/api/v1/tools/{tool_id}", headers=governance.kopf).json()
    assert tool["name"] == "Neuer Name"
    assert tool["metadaten"]["umgebung"] == "neu"
    assert tool["kategorie"] == "kernanwendung"


def test_stammdatenfelder_eines_importierten_tools_sind_gesperrt(
    client: TestClient, plattform, governance
) -> None:
    importiere(
        client, plattform, [{"typ": "tool", "externe_id": "TOOL-3", "name": "Importiert"}]
    )
    tool = client.get("/api/v1/tools", headers=governance.kopf).json()[0]
    assert set(tool["schreibgeschuetzte_felder"]) == {"name", "metadaten", "technologie"}

    verweigert = client.patch(
        f"/api/v1/tools/{tool['id']}", json={"name": "Von Hand"}, headers=governance.kopf
    )
    assert verweigert.status_code == 422
    assert "Ursprungssystem" in verweigert.json()["detail"]

    erlaubt = client.patch(
        f"/api/v1/tools/{tool['id']}", json={"kategorie": "hilfsmittel"}, headers=governance.kopf
    )
    assert erlaubt.status_code == 200


def test_manuell_angelegtes_tool_ist_frei_editierbar(
    client: TestClient, governance, organisation
) -> None:
    angelegt = client.post(
        "/api/v1/tools",
        json={
            "name": "Handangelegt",
            "beschreibung": "Manuell",
            "technologie": "python",
            "organisationseinheit_id": organisation["fin_de"],
        },
        headers=governance.kopf,
    )
    assert angelegt.status_code == 201
    tool = angelegt.json()
    assert tool["herkunft"] == "manuell"
    assert tool["status"] == "bestaetigt"
    assert tool["schreibgeschuetzte_felder"] == []
    geaendert = client.patch(
        f"/api/v1/tools/{tool['id']}", json={"name": "Umbenannt"}, headers=governance.kopf
    )
    assert geaendert.status_code == 200
    assert geaendert.json()["name"] == "Umbenannt"


def test_tool_mit_unbekannter_organisationseinheit(client: TestClient, governance) -> None:
    antwort = client.post(
        "/api/v1/tools",
        json={
            "name": "Waise",
            "organisationseinheit_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=governance.kopf,
    )
    assert antwort.status_code == 422


def test_importiertes_datenobjekt_behaelt_seine_kategorie(
    client: TestClient, plattform, governance
) -> None:
    importiere(
        client,
        plattform,
        [{"typ": "datenobjekt", "externe_id": "DO-1", "name": "Kreditorenstamm"}],
    )
    datenobjekt = client.get("/api/v1/datenobjekte", headers=governance.kopf).json()[0]
    client.patch(
        f"/api/v1/datenobjekte/{datenobjekt['id']}",
        json={"kategorie": "personenbezogen"},
        headers=governance.kopf,
    )
    importiere(
        client,
        plattform,
        [{"typ": "datenobjekt", "externe_id": "DO-1", "name": "Kreditorenstamm neu"}],
    )
    aktuell = client.get(
        f"/api/v1/datenobjekte/{datenobjekt['id']}", headers=governance.kopf
    ).json()
    assert aktuell["name"] == "Kreditorenstamm neu"
    assert aktuell["kategorie"] == "personenbezogen"


# --- Maximum-Vererbung (Abnahmekriterium 3.3) ----------------------------


def test_tool_zeigt_die_hoechste_geerbte_einstufung(
    client: TestClient, governance, owner, vertretung, prozess_daten
) -> None:
    """Abnahmekriterium 3.3: das Maximum ueber alle Prozesskanten."""
    gering = lege_prozess_an(
        client, owner, vertretung, prozess_daten, name="Gering", ausfallfolge="gering"
    )
    kritisch = lege_prozess_an(
        client,
        owner,
        vertretung,
        prozess_daten,
        name="Kritisch",
        ausfallfolge="kritisch",
        customer="extern",
    )
    tool = client.post(
        "/api/v1/tools", json={"name": "Gemeinsames Tool"}, headers=governance.kopf
    ).json()

    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": gering["id"]},
        headers=governance.kopf,
    )
    nur_gering = client.get(f"/api/v1/tools/{tool['id']}", headers=governance.kopf).json()
    assert nur_gering["geerbt"]["kritikalitaet"] == 1
    assert nur_gering["geerbt"]["reichweite"] == "bereich"

    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": kritisch["id"]},
        headers=governance.kopf,
    )
    beide = client.get(f"/api/v1/tools/{tool['id']}", headers=governance.kopf).json()
    assert beide["geerbt"]["kritikalitaet"] == 3
    assert beide["geerbt"]["reichweite"] == "extern"
    assert set(beide["geerbt"]["quelle_prozess_ids"]) == {gering["id"], kritisch["id"]}


def test_tool_erbt_tier_und_k_klassen_der_bewertungen(
    client: TestClient, governance, owner, vertretung, prozess_daten
) -> None:
    from tests.test_bewertung import antworten_fuer, profil_von

    niedrig = lege_prozess_an(client, owner, vertretung, prozess_daten, name="Niedrig")
    hoch = lege_prozess_an(client, owner, vertretung, prozess_daten, name="Hoch")
    for prozess, profil in ((niedrig, profil_von(ds=1)), (hoch, profil_von(ds=3, ur=2))):
        client.post(
            f"/api/v1/prozesse/{prozess['id']}/bewertungen",
            json={"modus": "vollstaendig", "antworten": antworten_fuer(profil)},
            headers=owner.kopf,
        )
    tool = client.post("/api/v1/tools", json={"name": "Erbe"}, headers=governance.kopf).json()
    for prozess in (niedrig, hoch):
        client.post(
            f"/api/v1/tools/{tool['id']}/prozesse",
            json={"prozessobjekt_id": prozess["id"]},
            headers=governance.kopf,
        )
    geerbt = client.get(f"/api/v1/tools/{tool['id']}", headers=governance.kopf).json()["geerbt"]
    assert geerbt["tier"] == 3
    assert "K9" in geerbt["k_klassen"]
    assert geerbt["k_klassen"] == sorted(geerbt["k_klassen"], key=lambda k: int(k[1:]))


def test_tool_ohne_prozess_erbt_nichts(client: TestClient, governance) -> None:
    tool = client.post("/api/v1/tools", json={"name": "Frei"}, headers=governance.kopf).json()
    assert tool["geerbt"] == {
        "kritikalitaet": 0,
        "reichweite": None,
        "tier": None,
        "mitbestimmung_flag": False,
        "k_klassen": [],
        "quelle_prozess_ids": [],
    }


def test_verknuepfung_loesen_und_doppelte_verknuepfung(
    client: TestClient, governance, owner, vertretung, prozess_daten
) -> None:
    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    tool = client.post("/api/v1/tools", json={"name": "Tool"}, headers=governance.kopf).json()
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    doppelt = client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    assert doppelt.status_code == 422

    geloest = client.delete(
        f"/api/v1/tools/{tool['id']}/prozesse/{prozess['id']}", headers=governance.kopf
    )
    assert geloest.status_code == 200
    assert geloest.json()["prozessobjekt_ids"] == []

    nochmal = client.delete(
        f"/api/v1/tools/{tool['id']}/prozesse/{prozess['id']}", headers=governance.kopf
    )
    assert nochmal.status_code == 404


# --- Datenobjekt-Kategorie wirkt auf den Prozess (Abnahmekriterium 3.4) --


def test_kategorie_des_datenobjekts_wirkt_im_prozess(
    client: TestClient, governance, owner, vertretung, prozess_daten
) -> None:
    """Abnahmekriterium 3.4: keine Duplizierung, der Prozess liest die Kategorie."""
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Zeiterfassung", "beschreibung": "Arbeitszeiten"},
        headers=governance.kopf,
    ).json()
    assert datenobjekt["kategorie"] is None

    prozess = lege_prozess_an(
        client,
        owner,
        vertretung,
        prozess_daten,
        input_datenobjekt_ids=[datenobjekt["id"]],
    )
    assert prozess["mitbestimmung_flag"] is False

    client.patch(
        f"/api/v1/datenobjekte/{datenobjekt['id']}",
        json={"kategorie": "mitarbeiterbezogen"},
        headers=governance.kopf,
    )
    aktualisiert = client.get(f"/api/v1/prozesse/{prozess['id']}", headers=owner.kopf).json()
    assert aktualisiert["mitbestimmung_flag"] is True
    # Die Kategorie steht weiterhin nur am Datenobjekt.
    assert aktualisiert["input_datenobjekt_ids"] == [datenobjekt["id"]]


def test_kategorieaenderung_wirkt_auch_ueber_die_prozesskette(
    client: TestClient, governance, owner, vertretung, prozess_daten
) -> None:
    datenobjekt = client.post(
        "/api/v1/datenobjekte", json={"name": "Personaldaten"}, headers=governance.kopf
    ).json()
    nachfolger = lege_prozess_an(
        client,
        owner,
        vertretung,
        prozess_daten,
        name="Nachfolger",
        input_datenobjekt_ids=[datenobjekt["id"]],
    )
    vorgaenger = lege_prozess_an(
        client,
        owner,
        vertretung,
        prozess_daten,
        name="Vorgaenger",
        ausfallfolge="keine",
        nachgelagert_ids=[nachfolger["id"]],
    )
    client.patch(
        f"/api/v1/datenobjekte/{datenobjekt['id']}",
        json={"kategorie": "mitarbeiterbezogen"},
        headers=governance.kopf,
    )
    # Das Flag haengt am Datenobjekt und schlaegt nur dort durch, wo es
    # tatsaechlich verknuepft ist — die Kritikalitaetskette bleibt unberuehrt.
    assert (
        client.get(f"/api/v1/prozesse/{nachfolger['id']}", headers=owner.kopf).json()[
            "mitbestimmung_flag"
        ]
        is True
    )
    assert (
        client.get(f"/api/v1/prozesse/{vorgaenger['id']}", headers=owner.kopf).json()[
            "mitbestimmung_flag"
        ]
        is False
    )


# --- Berechtigungen und Sichtbarkeit -------------------------------------


def test_technischer_owner_pflegt_sein_tool(
    client: TestClient, techniker, governance, organisation
) -> None:
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Landes-Tool", "organisationseinheit_id": organisation["fin_de"]},
        headers=techniker.kopf,
    )
    assert tool.status_code == 201
    geaendert = client.patch(
        f"/api/v1/tools/{tool.json()['id']}",
        json={"beschreibung": "Vom Techniker gepflegt"},
        headers=techniker.kopf,
    )
    assert geaendert.status_code == 200
    del governance


def test_fremdes_tool_ist_weder_sichtbar_noch_aenderbar(
    client: TestClient, governance, anmelden, organisation
) -> None:
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Fremd", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    fremder = anmelden("Ohne Rolle")
    assert client.get("/api/v1/tools", headers=fremder.kopf).json() == []
    assert client.get(f"/api/v1/tools/{tool['id']}", headers=fremder.kopf).status_code == 403
    assert (
        client.patch(
            f"/api/v1/tools/{tool['id']}", json={"beschreibung": "x"}, headers=fremder.kopf
        ).status_code
        == 403
    )


def test_prozess_owner_sieht_tools_seiner_prozesse(
    client: TestClient, governance, owner, vertretung, prozess_daten, organisation
) -> None:
    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Angehaengt", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    assert client.get("/api/v1/tools", headers=owner.kopf).json() == []
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    sichtbar = client.get("/api/v1/tools", headers=owner.kopf).json()
    assert [t["name"] for t in sichtbar] == ["Angehaengt"]


def test_nur_governance_entfernt_tools(client: TestClient, governance, techniker) -> None:
    tool = client.post(
        "/api/v1/tools", json={"name": "Wegwerf"}, headers=governance.kopf
    ).json()
    assert (
        client.delete(f"/api/v1/tools/{tool['id']}", headers=techniker.kopf).status_code == 403
    )
    assert (
        client.delete(f"/api/v1/tools/{tool['id']}", headers=governance.kopf).status_code == 204
    )
    assert client.get(f"/api/v1/tools/{tool['id']}", headers=governance.kopf).status_code == 404


def test_datenobjekt_owner_darf_kategorisieren(
    client: TestClient, governance, anmelden, rolle_geben, organisation
) -> None:
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Bereichsdaten", "fachbereich_id": organisation["fachbereich_finance"]},
        headers=governance.kopf,
    ).json()
    do_owner = anmelden("Datenobjekt-Owner")
    rolle_geben(
        do_owner.user_id, "datenobjekt_owner", "fachbereich", organisation["fachbereich_finance"]
    )
    antwort = client.patch(
        f"/api/v1/datenobjekte/{datenobjekt['id']}",
        json={"kategorie": "vertraulich"},
        headers=do_owner.kopf,
    )
    assert antwort.status_code == 200

    fremder = anmelden("Ohne Rolle")
    assert (
        client.patch(
            f"/api/v1/datenobjekte/{datenobjekt['id']}",
            json={"kategorie": "intern"},
            headers=fremder.kopf,
        ).status_code
        == 403
    )


def test_unbekanntes_asset_liefert_404(client: TestClient, governance) -> None:
    fehlt = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/v1/tools/{fehlt}", headers=governance.kopf).status_code == 404
    assert (
        client.get(f"/api/v1/datenobjekte/{fehlt}", headers=governance.kopf).status_code == 404
    )


# --- Filter und Tool-Datenobjekt-Kanten ----------------------------------


def test_filter_ohne_prozess_und_ohne_kategorie(
    client: TestClient, governance, owner, vertretung, prozess_daten
) -> None:
    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    verknuepft = client.post(
        "/api/v1/tools", json={"name": "Verknuepft"}, headers=governance.kopf
    ).json()
    client.post(
        f"/api/v1/tools/{verknuepft['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    client.post("/api/v1/tools", json={"name": "Waise"}, headers=governance.kopf)

    ohne = client.get("/api/v1/tools?ohne_prozess=true", headers=governance.kopf).json()
    assert [t["name"] for t in ohne] == ["Waise"]

    client.post(
        "/api/v1/datenobjekte",
        json={"name": "Ohne Kategorie"},
        headers=governance.kopf,
    )
    client.post(
        "/api/v1/datenobjekte",
        json={"name": "Mit Kategorie", "kategorie": "intern"},
        headers=governance.kopf,
    )
    unkategorisiert = client.get(
        "/api/v1/datenobjekte?ohne_kategorie=true", headers=governance.kopf
    ).json()
    assert [d["name"] for d in unkategorisiert] == ["Ohne Kategorie"]


def test_status_filter_auf_tools(client: TestClient, plattform, governance) -> None:
    importiere(client, plattform, [{"typ": "tool", "externe_id": "T-9", "name": "Neu"}])
    client.post("/api/v1/tools", json={"name": "Bestaetigt"}, headers=governance.kopf)
    unbestaetigt = client.get(
        "/api/v1/tools?status_filter=importiert_unbestaetigt", headers=governance.kopf
    ).json()
    assert [t["name"] for t in unbestaetigt] == ["Neu"]


def test_tool_liest_und_schreibt_datenobjekte(client: TestClient, governance) -> None:
    tool = client.post(
        "/api/v1/tools", json={"name": "Verarbeiter"}, headers=governance.kopf
    ).json()
    datenobjekt = client.post(
        "/api/v1/datenobjekte", json={"name": "Buchungen"}, headers=governance.kopf
    ).json()
    angelegt = client.post(
        f"/api/v1/tools/{tool['id']}/datenobjekte",
        json={"datenobjekt_id": datenobjekt["id"], "zugriffsart": "lesen_schreiben"},
        headers=governance.kopf,
    )
    assert angelegt.status_code == 201
    assert angelegt.json()["zugriffsart"] == "lesen_schreiben"

    doppelt = client.post(
        f"/api/v1/tools/{tool['id']}/datenobjekte",
        json={"datenobjekt_id": datenobjekt["id"]},
        headers=governance.kopf,
    )
    assert doppelt.status_code == 422

    kanten = client.get(
        f"/api/v1/tools/{tool['id']}/datenobjekte", headers=governance.kopf
    ).json()
    assert len(kanten) == 1
    assert kanten[0]["datenobjekt_id"] == datenobjekt["id"]


def test_datenobjekt_bestaetigen(client: TestClient, plattform, governance) -> None:
    importiere(
        client, plattform, [{"typ": "datenobjekt", "externe_id": "DO-9", "name": "Neu"}]
    )
    datenobjekt = client.get("/api/v1/datenobjekte", headers=governance.kopf).json()[0]
    assert datenobjekt["status"] == "importiert_unbestaetigt"
    antwort = client.post(
        f"/api/v1/datenobjekte/{datenobjekt['id']}/bestaetigung", headers=governance.kopf
    )
    assert antwort.status_code == 200
    assert antwort.json()["status"] == "bestaetigt"


def test_assetaenderungen_landen_im_nachweis(client: TestClient, governance, db) -> None:
    from app.models.audit import ChangeLog

    tool = client.post(
        "/api/v1/tools", json={"name": "Protokolliert"}, headers=governance.kopf
    ).json()
    client.patch(
        f"/api/v1/tools/{tool['id']}", json={"beschreibung": "neu"}, headers=governance.kopf
    )
    db.expire_all()
    aktionen = [
        e.aktion
        for e in db.query(ChangeLog).filter(ChangeLog.entity_type == "tool_objekte").all()
    ]
    assert aktionen == ["erstellt", "geaendert"]
