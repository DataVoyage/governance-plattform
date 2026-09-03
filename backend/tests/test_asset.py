"""Asset-Management — Abnahmekriterien Phase 3 (Architektur 8.3)."""

from __future__ import annotations

import uuid

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
    rolle_geben(nutzer.user_id, "technischer_owner", "organisationseinheit", organisation["fin_de"])
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
    client: TestClient, plattform, governance, owner, vertretung, prozess_daten, attestieren
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

    bestaetigt = client.post(f"/api/v1/tools/{tool['id']}/bestaetigung", headers=governance.kopf)
    assert bestaetigt.status_code == 200
    assert bestaetigt.json()["status"] == "bestaetigt"

    attestieren(governance.kopf, tool["id"])

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
    importiere(client, plattform, [{"typ": "tool", "externe_id": "TOOL-3", "name": "Importiert"}])
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
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren
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
    attestieren(governance.kopf, tool["id"])

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
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren
) -> None:
    from tests.test_bewertung import nutzlast, profil_von

    niedrig = lege_prozess_an(client, owner, vertretung, prozess_daten, name="Niedrig")
    hoch = lege_prozess_an(client, owner, vertretung, prozess_daten, name="Hoch")
    for prozess, profil in ((niedrig, profil_von(ds=1)), (hoch, profil_von(ds=3, ur=2))):
        client.post(
            f"/api/v1/prozesse/{prozess['id']}/bewertungen",
            json=nutzlast(profil),
            headers=owner.kopf,
        )
    tool = client.post("/api/v1/tools", json={"name": "Erbe"}, headers=governance.kopf).json()
    attestieren(governance.kopf, tool["id"])
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
        "beitraege": [],
    }


def test_verknuepfung_loesen_und_doppelte_verknuepfung(
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren
) -> None:
    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    tool = client.post("/api/v1/tools", json={"name": "Tool"}, headers=governance.kopf).json()
    attestieren(governance.kopf, tool["id"])
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
    client: TestClient, governance, owner, vertretung, prozess_daten, organisation
) -> None:
    """Abnahmekriterium 3.4: keine Duplizierung, der Prozess liest die Kategorie.

    Zugleich die Regel aus Leitdokument A.5: das Mitbestimmungsflag verlangt
    Personenbezug **und** eine Wirkung auf Einzelne. Die besondere Kategorie
    schliesst nach A.7 Entgelt, Gesundheit und Leistungsbewertung ein und
    erfuellt damit beide Haelften.
    """
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={
            "name": "Zeiterfassung",
            "beschreibung": "Arbeitszeiten",
            "fachbereich_id": organisation["fachbereich_finance"],
        },
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

    # Personenbezug allein genuegt nicht — A.5 verlangt eine Konjunktion.
    client.patch(
        f"/api/v1/datenobjekte/{datenobjekt['id']}",
        json={"kategorie": "personenbezogen"},
        headers=governance.kopf,
    )
    zwischenstand = client.get(f"/api/v1/prozesse/{prozess['id']}", headers=owner.kopf).json()
    assert zwischenstand["mitbestimmung_flag"] is False

    client.patch(
        f"/api/v1/datenobjekte/{datenobjekt['id']}",
        json={"kategorie": "besondere_kategorie"},
        headers=governance.kopf,
    )
    aktualisiert = client.get(f"/api/v1/prozesse/{prozess['id']}", headers=owner.kopf).json()
    assert aktualisiert["mitbestimmung_flag"] is True
    # Die Kategorie steht weiterhin nur am Datenobjekt.
    assert aktualisiert["input_datenobjekt_ids"] == [datenobjekt["id"]]


def test_kategorieaenderung_wirkt_auch_ueber_die_prozesskette(
    client: TestClient, governance, owner, vertretung, prozess_daten, organisation
) -> None:
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Personaldaten", "fachbereich_id": organisation["fachbereich_finance"]},
        headers=governance.kopf,
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
        json={"kategorie": "besondere_kategorie"},
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
    client: TestClient, governance, owner, vertretung, prozess_daten, organisation, attestieren
) -> None:
    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Angehaengt", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    attestieren(governance.kopf, tool["id"])
    assert client.get("/api/v1/tools", headers=owner.kopf).json() == []
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    sichtbar = client.get("/api/v1/tools", headers=owner.kopf).json()
    assert [t["name"] for t in sichtbar] == ["Angehaengt"]


def test_nur_governance_entfernt_tools(client: TestClient, governance, techniker) -> None:
    tool = client.post("/api/v1/tools", json={"name": "Wegwerf"}, headers=governance.kopf).json()
    assert client.delete(f"/api/v1/tools/{tool['id']}", headers=techniker.kopf).status_code == 403
    assert client.delete(f"/api/v1/tools/{tool['id']}", headers=governance.kopf).status_code == 204
    assert client.get(f"/api/v1/tools/{tool['id']}", headers=governance.kopf).status_code == 404


def test_fremdes_datenobjekt_ist_weder_lesbar_noch_aenderbar(
    client: TestClient, governance, anmelden, organisation
) -> None:
    """Die Liste zu filtern genuegt nicht — der Direktaufruf muss dieselbe Antwort geben.

    Wer die Kennung kennt, umgeht sonst die Liste und liest ueber die API, was
    ihm die Oberflaeche verbirgt. Auch die Wirkungsvorschau haengt daran: sie
    zaehlt Prozesse und Tool-Objekte an einem Datenobjekt.
    """
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={
            "name": "Fremde Bereichsdaten",
            "fachbereich_id": organisation["fachbereich_finance"],
        },
        headers=governance.kopf,
    ).json()
    fremder = anmelden("Ohne Rolle")
    assert client.get("/api/v1/datenobjekte", headers=fremder.kopf).json() == []
    assert (
        client.get(f"/api/v1/datenobjekte/{datenobjekt['id']}", headers=fremder.kopf).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/datenobjekte/{datenobjekt['id']}/wirkung", headers=fremder.kopf
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/datenobjekte/{datenobjekt['id']}",
            json={"kategorie": "vertraulich"},
            headers=fremder.kopf,
        ).status_code
        == 403
    )


def test_datenobjekt_owner_liest_sein_datenobjekt_direkt(
    client: TestClient, governance, anmelden, rolle_geben, organisation
) -> None:
    """Die Gegenprobe: im eigenen Bereich bleibt der Direktaufruf offen."""
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={
            "name": "Eigene Bereichsdaten",
            "fachbereich_id": organisation["fachbereich_finance"],
        },
        headers=governance.kopf,
    ).json()
    do_owner = anmelden("Datenobjekt-Owner")
    rolle_geben(
        do_owner.user_id, "datenobjekt_owner", "fachbereich", organisation["fachbereich_finance"]
    )
    assert (
        client.get(f"/api/v1/datenobjekte/{datenobjekt['id']}", headers=do_owner.kopf).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/datenobjekte/{datenobjekt['id']}/wirkung", headers=do_owner.kopf
        ).status_code
        == 200
    )


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
    assert client.get(f"/api/v1/datenobjekte/{fehlt}", headers=governance.kopf).status_code == 404


# --- Filter und Tool-Datenobjekt-Kanten ----------------------------------


def test_filter_ohne_prozess_und_ohne_kategorie(
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren, organisation
) -> None:
    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    verknuepft = client.post(
        "/api/v1/tools", json={"name": "Verknuepft"}, headers=governance.kopf
    ).json()
    attestieren(governance.kopf, verknuepft["id"])
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
        json={"name": "Ohne Kategorie", "fachbereich_id": organisation["fachbereich_finance"]},
        headers=governance.kopf,
    )
    client.post(
        "/api/v1/datenobjekte",
        json={
            "name": "Mit Kategorie",
            "kategorie": "intern",
            "fachbereich_id": organisation["fachbereich_finance"],
        },
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


def test_tool_liest_und_schreibt_datenobjekte(client: TestClient, governance, organisation) -> None:
    tool = client.post(
        "/api/v1/tools", json={"name": "Verarbeiter"}, headers=governance.kopf
    ).json()
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Buchungen", "fachbereich_id": organisation["fachbereich_finance"]},
        headers=governance.kopf,
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

    kanten = client.get(f"/api/v1/tools/{tool['id']}/datenobjekte", headers=governance.kopf).json()
    assert len(kanten) == 1
    assert kanten[0]["datenobjekt_id"] == datenobjekt["id"]


def test_datenobjekt_bestaetigen_heisst_zuordnen(
    client: TestClient, plattform, governance, organisation
) -> None:
    """Ein vorgefundenes Datenobjekt hat keinen Fachbereich; bestaetigen verlangt einen (7.2).

    Sonst gaebe es ein bestaetigtes Objekt, das niemandem gehoert — sichtbar
    nur global, klassifizierbar von niemandem.
    """
    importiere(client, plattform, [{"typ": "datenobjekt", "externe_id": "DO-9", "name": "Neu"}])
    datenobjekt = client.get("/api/v1/datenobjekte", headers=governance.kopf).json()[0]
    assert datenobjekt["status"] == "importiert_unbestaetigt"
    assert datenobjekt["fachbereich_id"] is None
    ohne = client.post(
        f"/api/v1/datenobjekte/{datenobjekt['id']}/bestaetigung", headers=governance.kopf
    )
    assert ohne.status_code == 422

    # Die Plattform darf den Anker setzen — nur solange das Objekt unbestaetigt ist.
    zuordnung = client.patch(
        f"/api/v1/datenobjekte/{datenobjekt['id']}",
        json={"fachbereich_id": organisation["fachbereich_finance"]},
        headers=plattform.kopf,
    )
    assert zuordnung.status_code == 200, zuordnung.text
    antwort = client.post(
        f"/api/v1/datenobjekte/{datenobjekt['id']}/bestaetigung", headers=plattform.kopf
    )
    assert antwort.status_code == 200
    assert antwort.json()["status"] == "bestaetigt"
    danach = client.patch(
        f"/api/v1/datenobjekte/{datenobjekt['id']}",
        json={"fachbereich_id": organisation["fachbereich_hr"]},
        headers=plattform.kopf,
    )
    assert danach.status_code == 403


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
        e.aktion for e in db.query(ChangeLog).filter(ChangeLog.entity_type == "tool_objekte").all()
    ]
    assert aktionen == ["erstellt", "geaendert"]


def test_datenobjekt_ohne_fachbereich_bleibt_global(
    client: TestClient, governance, anmelden, rolle_geben, organisation
) -> None:
    """Ein nicht zugeordnetes Datenobjekt ist nicht fuer jeden sichtbar.

    Sonst waere die Sichtbarkeitsregel aus Architektur 4.3 ausgehebelt: wer
    keine Rolle hat, saehe alles, was noch keinem Fachbereich zugeordnet ist.
    """
    client.post(
        "/api/v1/datenobjekte",
        json={"name": "Herrenlos", "fachbereich_id": organisation["fachbereich_finance"]},
        headers=governance.kopf,
    )
    fremder = anmelden("Ohne Rolle")
    assert client.get("/api/v1/datenobjekte", headers=fremder.kopf).json() == []

    im_bereich = anmelden("Im Fachbereich")
    rolle_geben(
        im_bereich.user_id, "prozess_owner", "organisationseinheit", organisation["fin_int"]
    )
    assert client.get("/api/v1/datenobjekte", headers=im_bereich.kopf).json() == []
    assert len(client.get("/api/v1/datenobjekte", headers=governance.kopf).json()) == 1


# --- Umsetzungsplan AP-2: Reifegrad 1, Kategorien, Wirkung ---------------


def test_datenobjekt_traegt_fachbereich_und_quellsystem(
    client: TestClient, governance, organisation
) -> None:
    """Reifegrad 1 aus Leitdokument A.7: Name, Kategorie, datenhaltende Stelle, Quellsystem.

    Die Stelle ist der Fachbereich — keine Person (docs/rollen-und-scopes.md, 7.1).
    """
    antwort = client.post(
        "/api/v1/datenobjekte",
        json={
            "name": "Entgeltdaten",
            "beschreibung": "Monatliche Abrechnung",
            "kategorie": "besondere_kategorie",
            "fachbereich_id": organisation["fachbereich_hr"],
            "quellsystem": "SAP HCM",
        },
        headers=governance.kopf,
    )
    assert antwort.status_code == 201, antwort.text
    datenobjekt = antwort.json()
    assert datenobjekt["fachbereich_id"] == organisation["fachbereich_hr"]
    assert datenobjekt["quellsystem"] == "SAP HCM"
    assert "owner_user_id" not in datenobjekt

    geaendert = client.patch(
        f"/api/v1/datenobjekte/{datenobjekt['id']}",
        json={"quellsystem": "SAP HCM (Mandant 100)"},
        headers=governance.kopf,
    )
    assert geaendert.json()["quellsystem"] == "SAP HCM (Mandant 100)"


def test_datenobjekt_ohne_fachbereich_gibt_es_nicht(client: TestClient, governance) -> None:
    """Auch die Governance legt keine herrenlose Quelle an (7.2)."""
    antwort = client.post(
        "/api/v1/datenobjekte", json={"name": "Niemandes Daten"}, headers=governance.kopf
    )
    assert antwort.status_code == 422
    assert "Fachbereich" in antwort.json()["detail"]


def test_mitarbeiterbezogen_ist_keine_kategorie_mehr(
    client: TestClient, governance, organisation
) -> None:
    """Leitdokument A.7 schliesst sie ausdruecklich aus (siehe E-19)."""
    antwort = client.post(
        "/api/v1/datenobjekte",
        json={
            "name": "Zeiterfassung",
            "kategorie": "mitarbeiterbezogen",
            "fachbereich_id": organisation["fachbereich_finance"],
        },
        headers=governance.kopf,
    )
    assert antwort.status_code == 422, antwort.text


def test_wirkung_zeigt_betroffene_prozesse_und_tools(
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren, organisation
) -> None:
    """Simulation vor Entscheidung (Leitdokument A.4.7)."""
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Personaldaten", "fachbereich_id": organisation["fachbereich_finance"]},
        headers=governance.kopf,
    ).json()
    prozess = lege_prozess_an(
        client,
        owner,
        vertretung,
        prozess_daten,
        name="Personalbericht",
        input_datenobjekt_ids=[datenobjekt["id"]],
    )
    tool = client.post(
        "/api/v1/tools", json={"name": "Berichtsskript"}, headers=governance.kopf
    ).json()
    attestieren(governance.kopf, tool["id"])
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    client.post(
        f"/api/v1/tools/{tool['id']}/datenobjekte",
        json={"datenobjekt_id": datenobjekt["id"], "zugriffsart": "lesen"},
        headers=governance.kopf,
    )

    antwort = client.get(
        f"/api/v1/datenobjekte/{datenobjekt['id']}/wirkung?kategorie=besondere_kategorie",
        headers=governance.kopf,
    )
    assert antwort.status_code == 200, antwort.text
    wirkung = antwort.json()
    assert wirkung["kategorie_alt"] is None
    assert wirkung["kategorie_neu"] == "besondere_kategorie"
    assert [p["name"] for p in wirkung["prozesse"]] == ["Personalbericht"]
    assert wirkung["prozesse"][0]["als_input"] is True
    assert wirkung["prozesse"][0]["mitbestimmung_flag"] is False
    assert wirkung["prozesse"][0]["mitbestimmung_flag_neu"] is True
    assert wirkung["mitbestimmung_neu"] == 1
    assert [t["name"] for t in wirkung["tools"]] == ["Berichtsskript"]
    assert wirkung["tools"][0]["zugriffsart"] == "lesen"

    # Die Vorschau aendert nichts: das Datenobjekt bleibt unkategorisiert.
    unveraendert = client.get(
        f"/api/v1/datenobjekte/{datenobjekt['id']}", headers=governance.kopf
    ).json()
    assert unveraendert["kategorie"] is None


def test_wirkung_ohne_kategorie_beschreibt_den_stand(
    client: TestClient, governance, owner, vertretung, prozess_daten, organisation
) -> None:
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Artikelstamm", "fachbereich_id": organisation["fachbereich_finance"]},
        headers=governance.kopf,
    ).json()
    lege_prozess_an(
        client,
        owner,
        vertretung,
        prozess_daten,
        name="Sortimentspflege",
        output_datenobjekt_ids=[datenobjekt["id"]],
    )
    wirkung = client.get(
        f"/api/v1/datenobjekte/{datenobjekt['id']}/wirkung", headers=governance.kopf
    ).json()
    assert wirkung["kategorie_neu"] is None
    assert wirkung["prozesse"][0]["als_output"] is True
    assert wirkung["mitbestimmung_neu"] == 0


def test_job_rechnet_ableitungen_nach(
    client: TestClient, governance, owner, vertretung, prozess_daten, db, organisation
) -> None:
    """Ein Regelwechsel darf den Bestand nicht still veralten lassen (E-19)."""
    from app import jobs
    from app.models.governance import Prozessobjekt

    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={
            "name": "Gehaltsliste",
            "kategorie": "besondere_kategorie",
            "fachbereich_id": organisation["fachbereich_finance"],
        },
        headers=governance.kopf,
    ).json()
    prozess = lege_prozess_an(
        client,
        owner,
        vertretung,
        prozess_daten,
        input_datenobjekt_ids=[datenobjekt["id"]],
    )
    assert prozess["mitbestimmung_flag"] is True

    # Ein veralteter Stand, wie ihn ein Regelwechsel hinterlassen wuerde.
    gespeichert = db.get(Prozessobjekt, uuid.UUID(prozess["id"]))
    gespeichert.mitbestimmung_flag = False
    gespeichert.kritikalitaet = 0
    db.commit()

    assert jobs.main(["ableitungen"]) == 0

    aktualisiert = client.get(f"/api/v1/prozesse/{prozess['id']}", headers=owner.kopf).json()
    assert aktualisiert["mitbestimmung_flag"] is True
    assert aktualisiert["kritikalitaet"] == 2


# --- Attestierungen nach Leitdokument A.6 (Umsetzungsplan AP-3) ----------


def test_ohne_attestierung_keine_prozessverknuepfung(
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren
) -> None:
    """A.6: die drei Erklaerungen tragen die Triage — vorher gibt es keine Kante."""
    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    tool = client.post("/api/v1/tools", json={"name": "Skript"}, headers=governance.kopf).json()
    assert tool["attestierung_vollstaendig"] is False
    assert tool["attest_mensch_dazwischen"] is None

    verweigert = client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    assert verweigert.status_code == 422
    assert "Attestierungen" in verweigert.json()["detail"]

    attestieren(governance.kopf, tool["id"])
    erlaubt = client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    assert erlaubt.status_code == 201


def test_attestierung_traegt_person_und_zeitpunkt(
    client: TestClient, governance, attestieren
) -> None:
    """A.6 verlangt die Erklaerung „mit Namen"; beides setzt der Server."""
    tool = client.post("/api/v1/tools", json={"name": "Skript"}, headers=governance.kopf).json()
    erklaert = attestieren(governance.kopf, tool["id"], attest_undeklarierte_quellen=True)
    assert erklaert["attestierung_vollstaendig"] is True
    assert erklaert["attest_undeklarierte_quellen"] is True
    assert erklaert["attestiert_von_user_id"] == governance.user_id
    assert erklaert["attestiert_am"] is not None


def test_teilweise_attestierung_wird_abgewiesen(client: TestClient, governance) -> None:
    """Eine Erklaerung zu einem Zeitpunkt, keine Sammlung einzelner Felder."""
    tool = client.post("/api/v1/tools", json={"name": "Skript"}, headers=governance.kopf).json()
    antwort = client.put(
        f"/api/v1/tools/{tool['id']}/attestierungen",
        json={"attest_mensch_dazwischen": True},
        headers=governance.kopf,
    )
    assert antwort.status_code == 422


def test_fremde_duerfen_nicht_attestieren(client: TestClient, governance, techniker) -> None:
    tool = client.post("/api/v1/tools", json={"name": "Fremd"}, headers=governance.kopf).json()
    antwort = client.put(
        f"/api/v1/tools/{tool['id']}/attestierungen",
        json={
            "attest_entscheidung_ueber_personen": False,
            "attest_mensch_dazwischen": True,
            "attest_undeklarierte_quellen": False,
        },
        headers=techniker.kopf,
    )
    assert antwort.status_code == 403


# --- „Verändert" gegen „gestaltet" (Leitdokument A.6) -------------------


def test_wirkungsart_bleibt_offen_solange_niemand_erklaert_hat(
    client: TestClient, governance
) -> None:
    """Ohne Attestierung 2 darf niemand „gestaltend" behaupten."""
    tool = client.post("/api/v1/tools", json={"name": "Unklar"}, headers=governance.kopf).json()
    assert tool["wirkungsart"] is None
    assert tool["wirkungsart_grund"] == "offen"


def test_nur_lesendes_tool_mit_mensch_dazwischen_gestaltet(
    client: TestClient, governance, attestieren, organisation
) -> None:
    tool = client.post("/api/v1/tools", json={"name": "Bericht"}, headers=governance.kopf).json()
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Umsaetze", "fachbereich_id": organisation["fachbereich_finance"]},
        headers=governance.kopf,
    ).json()
    client.post(
        f"/api/v1/tools/{tool['id']}/datenobjekte",
        json={"datenobjekt_id": datenobjekt["id"], "zugriffsart": "lesen"},
        headers=governance.kopf,
    )
    erklaert = attestieren(governance.kopf, tool["id"])
    assert erklaert["wirkungsart"] == "gestaltend"
    assert erklaert["wirkungsart_grund"] == "nur_lesend"


def test_kein_mensch_dazwischen_macht_auch_reines_lesen_veraendernd(
    client: TestClient, governance, attestieren, organisation
) -> None:
    """Die Warnung aus A.6: das sieht man an keiner Berechtigung."""
    tool = client.post("/api/v1/tools", json={"name": "Autopilot"}, headers=governance.kopf).json()
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Bewerbungen", "fachbereich_id": organisation["fachbereich_finance"]},
        headers=governance.kopf,
    ).json()
    client.post(
        f"/api/v1/tools/{tool['id']}/datenobjekte",
        json={"datenobjekt_id": datenobjekt["id"], "zugriffsart": "lesen"},
        headers=governance.kopf,
    )
    erklaert = attestieren(governance.kopf, tool["id"], attest_mensch_dazwischen=False)
    assert erklaert["wirkungsart"] == "veraendernd"
    assert erklaert["wirkungsart_grund"] == "kein_mensch"


def test_schreibzugriff_macht_das_tool_veraendernd(
    client: TestClient, governance, attestieren, organisation
) -> None:
    tool = client.post("/api/v1/tools", json={"name": "Bucher"}, headers=governance.kopf).json()
    attestieren(governance.kopf, tool["id"])
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Belege", "fachbereich_id": organisation["fachbereich_finance"]},
        headers=governance.kopf,
    ).json()
    client.post(
        f"/api/v1/tools/{tool['id']}/datenobjekte",
        json={"datenobjekt_id": datenobjekt["id"], "zugriffsart": "schreiben"},
        headers=governance.kopf,
    )
    geladen = client.get(f"/api/v1/tools/{tool['id']}", headers=governance.kopf).json()
    assert geladen["wirkungsart"] == "veraendernd"
    assert geladen["wirkungsart_grund"] == "schreibzugriff"


# --- Zweckbindung (Leitdokument A.4.6) -----------------------------------


def test_zweckbindung_erkennt_datenobjekt_ausserhalb_des_prozessrahmens(
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren, organisation
) -> None:
    """„Tool liest D im Rahmen von P" — oder eben erkennbar daneben."""
    erlaubt = client.post(
        "/api/v1/datenobjekte",
        json={
            "name": "Kreditorenstamm",
            "kategorie": "intern",
            "fachbereich_id": organisation["fachbereich_finance"],
        },
        headers=governance.kopf,
    ).json()
    fremd = client.post(
        "/api/v1/datenobjekte",
        json={
            "name": "Gesundheitsakte",
            "kategorie": "besondere_kategorie",
            "fachbereich_id": organisation["fachbereich_finance"],
        },
        headers=governance.kopf,
    ).json()
    prozess = lege_prozess_an(
        client, owner, vertretung, prozess_daten, input_datenobjekt_ids=[erlaubt["id"]]
    )
    tool = client.post("/api/v1/tools", json={"name": "Skript"}, headers=governance.kopf).json()
    attestieren(governance.kopf, tool["id"])
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    for datenobjekt in (erlaubt, fremd):
        client.post(
            f"/api/v1/tools/{tool['id']}/datenobjekte",
            json={"datenobjekt_id": datenobjekt["id"], "zugriffsart": "lesen"},
            headers=governance.kopf,
        )

    nutzung = {
        eintrag["name"]: eintrag
        for eintrag in client.get(
            f"/api/v1/tools/{tool['id']}/datenobjekte", headers=governance.kopf
        ).json()
    }
    assert nutzung["Kreditorenstamm"]["im_prozessrahmen"] is True
    assert nutzung["Kreditorenstamm"]["kategorie_gedeckt"] is True
    assert nutzung["Gesundheitsakte"]["im_prozessrahmen"] is False
    assert nutzung["Gesundheitsakte"]["kategorie_gedeckt"] is False
    assert nutzung["Gesundheitsakte"]["kategorie"] == "besondere_kategorie"


def test_gleiche_kategorie_deckt_das_datenobjekt_nur_schwach(
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren, organisation
) -> None:
    """Der schwaechere Test aus A.4.6: Kategorie gedeckt, Objekt nicht erklaert."""
    erklaert = client.post(
        "/api/v1/datenobjekte",
        json={
            "name": "Kreditorenstamm",
            "kategorie": "intern",
            "fachbereich_id": organisation["fachbereich_finance"],
        },
        headers=governance.kopf,
    ).json()
    weiteres = client.post(
        "/api/v1/datenobjekte",
        json={
            "name": "Debitorenstamm",
            "kategorie": "intern",
            "fachbereich_id": organisation["fachbereich_finance"],
        },
        headers=governance.kopf,
    ).json()
    prozess = lege_prozess_an(
        client, owner, vertretung, prozess_daten, input_datenobjekt_ids=[erklaert["id"]]
    )
    tool = client.post("/api/v1/tools", json={"name": "Skript"}, headers=governance.kopf).json()
    attestieren(governance.kopf, tool["id"])
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    client.post(
        f"/api/v1/tools/{tool['id']}/datenobjekte",
        json={"datenobjekt_id": weiteres["id"], "zugriffsart": "lesen"},
        headers=governance.kopf,
    )
    eintrag = client.get(
        f"/api/v1/tools/{tool['id']}/datenobjekte", headers=governance.kopf
    ).json()[0]
    assert eintrag["im_prozessrahmen"] is False
    assert eintrag["kategorie_gedeckt"] is True


def test_zugriffsart_aendern_und_kante_loesen(client: TestClient, governance, organisation) -> None:
    tool = client.post("/api/v1/tools", json={"name": "Skript"}, headers=governance.kopf).json()
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Belege", "fachbereich_id": organisation["fachbereich_finance"]},
        headers=governance.kopf,
    ).json()
    client.post(
        f"/api/v1/tools/{tool['id']}/datenobjekte",
        json={"datenobjekt_id": datenobjekt["id"], "zugriffsart": "lesen"},
        headers=governance.kopf,
    )
    geaendert = client.patch(
        f"/api/v1/tools/{tool['id']}/datenobjekte/{datenobjekt['id']}",
        json={"zugriffsart": "lesen_schreiben"},
        headers=governance.kopf,
    )
    assert geaendert.status_code == 200
    assert geaendert.json()["zugriffsart"] == "lesen_schreiben"

    geloest = client.delete(
        f"/api/v1/tools/{tool['id']}/datenobjekte/{datenobjekt['id']}", headers=governance.kopf
    )
    assert geloest.status_code == 204
    assert (
        client.get(f"/api/v1/tools/{tool['id']}/datenobjekte", headers=governance.kopf).json() == []
    )

    nochmal = client.delete(
        f"/api/v1/tools/{tool['id']}/datenobjekte/{datenobjekt['id']}", headers=governance.kopf
    )
    assert nochmal.status_code == 404
    assert (
        client.patch(
            f"/api/v1/tools/{tool['id']}/datenobjekte/{datenobjekt['id']}",
            json={"zugriffsart": "lesen"},
            headers=governance.kopf,
        ).status_code
        == 404
    )


def test_datenkante_steht_im_changelog(client: TestClient, governance, db, organisation) -> None:
    """Architektur 10.4: kein schreibender Vorgang ohne Nachweis."""
    from app.models.audit import ChangeLog

    tool = client.post("/api/v1/tools", json={"name": "Skript"}, headers=governance.kopf).json()
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Belege", "fachbereich_id": organisation["fachbereich_finance"]},
        headers=governance.kopf,
    ).json()
    client.post(
        f"/api/v1/tools/{tool['id']}/datenobjekte",
        json={"datenobjekt_id": datenobjekt["id"], "zugriffsart": "lesen"},
        headers=governance.kopf,
    )
    db.expire_all()
    eintraege = [
        eintrag
        for eintrag in db.query(ChangeLog).all()
        if eintrag.entity_type == "tool_objekte"
        and "Nutzt Datenobjekt" in eintrag.akteur_beschreibung
    ]
    assert len(eintraege) == 1
    assert eintraege[0].nachher["zugriffsart"] == "lesen"


# --- Geerbtes Maximum mit Quellenangabe (Leitdokument A.4.4) ------------


def test_geerbtes_maximum_nennt_die_massgebliche_kante(
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren
) -> None:
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
    tool = client.post("/api/v1/tools", json={"name": "Beides"}, headers=governance.kopf).json()
    attestieren(governance.kopf, tool["id"])
    for prozess in (gering, kritisch):
        client.post(
            f"/api/v1/tools/{tool['id']}/prozesse",
            json={"prozessobjekt_id": prozess["id"]},
            headers=governance.kopf,
        )
    geerbt = client.get(f"/api/v1/tools/{tool['id']}", headers=governance.kopf).json()["geerbt"]
    beitraege = {b["name"]: b for b in geerbt["beitraege"]}
    assert beitraege["Kritisch"]["massgeblich"] is True
    assert beitraege["Kritisch"]["kritikalitaet"] == 3
    assert beitraege["Gering"]["massgeblich"] is False


# --- Attestierung 1 als zweite Quelle der Mitbestimmung (A.5, E-19) -----


def test_attestierung_ueber_personen_macht_den_prozess_mitbestimmungsrelevant(
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren, organisation
) -> None:
    """Personenbezug allein genuegt nicht — die erklaerte Wirkung schon."""
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={
            "name": "Kontaktdaten",
            "kategorie": "personenbezogen",
            "fachbereich_id": organisation["fachbereich_finance"],
        },
        headers=governance.kopf,
    ).json()
    prozess = lege_prozess_an(
        client, owner, vertretung, prozess_daten, input_datenobjekt_ids=[datenobjekt["id"]]
    )
    assert prozess["mitbestimmung_flag"] is False

    tool = client.post("/api/v1/tools", json={"name": "Bewerter"}, headers=governance.kopf).json()
    attestieren(governance.kopf, tool["id"], attest_entscheidung_ueber_personen=True)
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    danach = client.get(f"/api/v1/prozesse/{prozess['id']}", headers=owner.kopf).json()
    assert danach["mitbestimmung_flag"] is True

    client.delete(f"/api/v1/tools/{tool['id']}/prozesse/{prozess['id']}", headers=governance.kopf)
    geloest = client.get(f"/api/v1/prozesse/{prozess['id']}", headers=owner.kopf).json()
    assert geloest["mitbestimmung_flag"] is False


def test_lauftyp_und_stellvertretung_am_tool(
    client: TestClient, governance, techniker, organisation
) -> None:
    tool = client.post(
        "/api/v1/tools",
        json={
            "name": "Nachtlauf",
            "technologie": "python-kubernetes",
            "lauftyp": "geplant",
            "technischer_owner_user_id": techniker.user_id,
            "stellvertretung_user_id": governance.user_id,
            "organisationseinheit_id": organisation["fin_de"],
        },
        headers=governance.kopf,
    )
    assert tool.status_code == 201, tool.text
    assert tool.json()["lauftyp"] == "geplant"
    assert tool.json()["stellvertretung_user_id"] == governance.user_id

    geaendert = client.patch(
        f"/api/v1/tools/{tool.json()['id']}",
        json={"lauftyp": "interaktiv"},
        headers=techniker.kopf,
    )
    assert geaendert.status_code == 200
    assert geaendert.json()["lauftyp"] == "interaktiv"


def test_nachtraegliche_attestierung_zieht_die_ableitung_nach(
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren, organisation
) -> None:
    """Wer seine Erklaerung korrigiert, korrigiert damit auch das Flag."""
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={
            "name": "Kontaktdaten",
            "kategorie": "personenbezogen",
            "fachbereich_id": organisation["fachbereich_finance"],
        },
        headers=governance.kopf,
    ).json()
    prozess = lege_prozess_an(
        client, owner, vertretung, prozess_daten, input_datenobjekt_ids=[datenobjekt["id"]]
    )
    tool = client.post("/api/v1/tools", json={"name": "Bewerter"}, headers=governance.kopf).json()
    attestieren(governance.kopf, tool["id"])
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    assert (
        client.get(f"/api/v1/prozesse/{prozess['id']}", headers=owner.kopf).json()[
            "mitbestimmung_flag"
        ]
        is False
    )

    attestieren(governance.kopf, tool["id"], attest_entscheidung_ueber_personen=True)
    assert (
        client.get(f"/api/v1/prozesse/{prozess['id']}", headers=owner.kopf).json()[
            "mitbestimmung_flag"
        ]
        is True
    )


# --- Rollen und Scopes: Datenobjekte (docs/rollen-und-scopes.md, Abschnitt 7) -


@pytest.fixture
def datenowner(anmelden, rolle_geben, organisation):
    nutzer = anmelden("Datenobjekt-Owner Finance", subject="sub-datenowner")
    rolle_geben(
        nutzer.user_id, "datenobjekt_owner", "fachbereich", organisation["fachbereich_finance"]
    )
    return nutzer


def _quelle(client: TestClient, wer, name: str, fachbereich_id: str, **weitere) -> dict:
    antwort = client.post(
        "/api/v1/datenobjekte",
        json={"name": name, "fachbereich_id": fachbereich_id, **weitere},
        headers=wer.kopf,
    )
    assert antwort.status_code == 201, antwort.text
    return antwort.json()


def test_prozess_owner_sieht_nur_die_quellen_seiner_prozesse(
    client: TestClient, governance, owner, vertretung, prozess_daten, organisation
) -> None:
    """7.3: ueber die Referenz, nicht ueber den Fachbereich.

    Der Prozess-Owner hat den Bereich Finance — aber keinen Grund, die
    Kassenbelege zu sehen, wenn keiner seiner Prozesse sie nutzt.
    """
    fin = organisation["fachbereich_finance"]
    genutzt = _quelle(client, governance, "Kreditorenstamm", fin)
    ungenutzt = _quelle(client, governance, "Kassenbelege", fin)
    lege_prozess_an(client, owner, vertretung, prozess_daten, input_datenobjekt_ids=[genutzt["id"]])

    sichtbar = [d["id"] for d in client.get("/api/v1/datenobjekte", headers=owner.kopf).json()]
    assert sichtbar == [genutzt["id"]]
    assert (
        client.get(f"/api/v1/datenobjekte/{genutzt['id']}", headers=owner.kopf).status_code == 200
    )
    assert (
        client.get(f"/api/v1/datenobjekte/{ungenutzt['id']}", headers=owner.kopf).status_code == 403
    )
    # Der Katalog kennt beide — mit vier Feldern, nicht mehr.
    katalog = client.get("/api/v1/datenobjekte/katalog", headers=owner.kopf).json()
    assert {k["name"] for k in katalog} == {"Kreditorenstamm", "Kassenbelege"}
    assert set(katalog[0]) == {"id", "name", "fachbereich_id", "kategorie", "quellsystem"}


def test_scope_zaehlt_nur_fuer_seine_rolle(
    client: TestClient, governance, anmelden, rolle_geben, organisation
) -> None:
    """Ein Prozess-Umsetzer in Finance DE hat den Bereich, aber nicht das Recht (Abschnitt 2)."""
    _quelle(client, governance, "Kassenbelege", organisation["fachbereich_finance"])
    umsetzer = anmelden("Umsetzer")
    rolle_geben(
        umsetzer.user_id, "prozess_umsetzer", "organisationseinheit", organisation["fin_de"]
    )
    assert client.get("/api/v1/datenobjekte", headers=umsetzer.kopf).json() == []


def test_gebender_prozess_pflegt_stammdaten_aber_nicht_die_kategorie(
    client: TestClient, governance, owner, vertretung, prozess_daten, datenowner, organisation
) -> None:
    """7.2 und 7.4: der Fachbereich kommt vom Prozessgeber, die Kategorie bleibt bei der Stelle."""
    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    antwort = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Zahllauf", "prozessobjekt_id": prozess["id"], "quellsystem": "SAP FI"},
        headers=owner.kopf,
    )
    assert antwort.status_code == 201, antwort.text
    quelle = antwort.json()
    assert quelle["fachbereich_id"] == organisation["fachbereich_finance"]
    assert quelle["rechte"] == {
        "bearbeiten": True,
        "kategorisieren": False,
        "anker_aendern": False,
        "bestaetigen": False,
    }
    nachgeladen = client.get(f"/api/v1/prozesse/{prozess['id']}", headers=owner.kopf).json()
    assert quelle["id"] in nachgeladen["output_datenobjekt_ids"]

    pfad = f"/api/v1/datenobjekte/{quelle['id']}"
    assert (
        client.patch(pfad, json={"quellsystem": "SAP S/4"}, headers=owner.kopf).status_code == 200
    )
    assert client.patch(pfad, json={"kategorie": "intern"}, headers=owner.kopf).status_code == 403
    assert (
        client.patch(
            pfad, json={"fachbereich_id": organisation["fachbereich_hr"]}, headers=owner.kopf
        ).status_code
        == 403
    )
    # Der Datenobjekt-Owner des Fachbereichs klassifiziert — und nur er wandert nicht.
    assert (
        client.patch(pfad, json={"kategorie": "intern"}, headers=datenowner.kopf).status_code == 200
    )
    assert (
        client.patch(
            pfad, json={"fachbereich_id": organisation["fachbereich_hr"]}, headers=datenowner.kopf
        ).status_code
        == 403
    )
    assert (
        client.patch(
            pfad, json={"fachbereich_id": organisation["fachbereich_hr"]}, headers=governance.kopf
        ).status_code
        == 200
    )


def test_fremder_prozess_gibt_keinen_output(
    client: TestClient, governance, owner, anmelden, prozess_daten, organisation
) -> None:
    vertretung = anmelden("Vertretung HR", subject="sub-vertretung-hr")
    fremd = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(
            governance.user_id,
            vertretung.user_id,
            prozessgeber_org_id=organisation["hr_int"],
        ),
        headers=governance.kopf,
    )
    assert fremd.status_code == 201, fremd.text
    antwort = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Nicht meine", "prozessobjekt_id": fremd.json()["id"]},
        headers=owner.kopf,
    )
    assert antwort.status_code == 403


def test_datenobjekt_owner_legt_nur_im_eigenen_fachbereich_an(
    client: TestClient, datenowner, organisation
) -> None:
    fremd = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Personaldaten", "fachbereich_id": organisation["fachbereich_hr"]},
        headers=datenowner.kopf,
    )
    assert fremd.status_code == 403
    eigen = _quelle(client, datenowner, "Kreditorenstamm", organisation["fachbereich_finance"])
    assert eigen["rechte"]["kategorisieren"] is True
    assert eigen["rechte"]["anker_aendern"] is False


def test_katalog_nur_fuer_rollentraeger(
    client: TestClient, governance, anmelden, organisation
) -> None:
    _quelle(client, governance, "Kassenbelege", organisation["fachbereich_finance"])
    niemand = anmelden("Ohne Rolle")
    assert client.get("/api/v1/datenobjekte/katalog", headers=niemand.kopf).status_code == 403
    assert client.get("/api/v1/datenobjekte", headers=niemand.kopf).json() == []
