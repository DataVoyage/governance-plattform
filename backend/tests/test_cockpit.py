"""Cockpit — Abnahmekriterien Phase 6 (Architektur 8.7, Leitdokument A.14)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.services.cockpit import ZEILEN
from app.services.selbstverpflichtung import AUSSAGE_RAHMEN_EINGEHALTEN
from tests.test_bewertung import nutzlast, profil_von

#: Die zehn Zeilen aus Leitdokument A.14.
ERWARTETE_ZEILEN = [
    "prozesse_ohne_owner",
    "assets_ohne_prozess",
    "non_compliant",
    "rahmenabweichungen",
    "datenobjekte_ohne_kategorie",
    "kritikalitaetsketten",
    "tier_verteilung",
    "inaktive_assets",
    "ueberfaellige_selbstverpflichtungen",
    "attestierungen_veraltet",
    "widersprueche",
    "antwort_widerspricht_datenlage",
    "technologie_erfuellt_klasse_nicht",
    "altanwendungen",
]

P_AUSSAGEN = ["PE1", "PE2", "PE3", "PE4", "PE5", "PE6"]
T_AUSSAGEN = ["TO1", "TO2", "TO3", "TO4", "TO5", "TO6"]


@pytest.fixture
def governance(anmelden, rolle_geben):
    nutzer = anmelden("Governance", subject="sub-gov")
    rolle_geben(nutzer.user_id, "governance", "global")
    return nutzer


@pytest.fixture
def owner(anmelden, rolle_geben, organisation):
    nutzer = anmelden("Prozess-Owner", subject="sub-owner")
    rolle_geben(nutzer.user_id, "prozess_owner", "organisationseinheit", organisation["fin_int"])
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


def bewerte(client: TestClient, anmeldung, prozess_id: str, **profil):
    return client.post(
        f"/api/v1/prozesse/{prozess_id}/bewertungen",
        json=nutzlast(profil_von(**profil)),
        headers=anmeldung.kopf,
    ).json()["bewertung"]


def zeile(client: TestClient, anmeldung, schluessel: str, abfrage: str = ""):
    antwort = client.get(f"/api/v1/cockpit/{schluessel}{abfrage}", headers=anmeldung.kopf)
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


# --- Abnahmekriterium 6.1: jede Zeile ist eine eigene Ansicht ------------


def test_jede_zeile_aus_a14_ist_aufrufbar(client: TestClient, governance) -> None:
    assert list(ZEILEN) == ERWARTETE_ZEILEN
    uebersicht = client.get("/api/v1/cockpit", headers=governance.kopf).json()
    assert [z["schluessel"] for z in uebersicht] == ERWARTETE_ZEILEN
    for eintrag in uebersicht:
        assert eintrag["titel"]
        assert eintrag["beschreibung"]
        einzeln = zeile(client, governance, eintrag["schluessel"])
        assert einzeln["schluessel"] == eintrag["schluessel"]
        assert einzeln["anzahl"] == eintrag["anzahl"]


def test_unbekannte_zeile_liefert_404(client: TestClient, governance) -> None:
    antwort = client.get("/api/v1/cockpit/gibt-es-nicht", headers=governance.kopf)
    assert antwort.status_code == 404


# --- Abnahmekriterium 6.2: jeder Eintrag traegt sein Ziel ----------------


def test_eintraege_verweisen_auf_das_vorgefilterte_zielmodul(
    client: TestClient, governance, owner, vertretung, prozess_daten, organisation
) -> None:
    datenobjekt = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Ohne Kategorie", "fachbereich_id": organisation["fachbereich_finance"]},
        headers=governance.kopf,
    ).json()
    treffer = zeile(client, governance, "datenobjekte_ohne_kategorie")
    assert treffer["anzahl"] == 1
    eintrag = treffer["eintraege"][0]
    assert eintrag["id"] == datenobjekt["id"]
    assert eintrag["ziel_modul"] == "datenobjekte"
    assert eintrag["ziel_filter"] == {"ohne_kategorie": "true"}

    # Der Filter fuehrt tatsaechlich zum Treffer.
    gefiltert = client.get(
        "/api/v1/datenobjekte?ohne_kategorie=true", headers=governance.kopf
    ).json()
    assert [d["id"] for d in gefiltert] == [datenobjekt["id"]]


def test_assets_ohne_prozess_zeigen_auf_das_tool(
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren, organisation
) -> None:
    waise = client.post(
        "/api/v1/tools",
        json={"name": "Waise", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    verknuepft = client.post(
        "/api/v1/tools",
        json={"name": "Verknuepft", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    attestieren(governance.kopf, verknuepft["id"])
    client.post(
        f"/api/v1/tools/{verknuepft['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    treffer = zeile(client, governance, "assets_ohne_prozess")
    assert [e["titel"] for e in treffer["eintraege"]] == ["Waise"]
    assert treffer["eintraege"][0]["ziel_filter"] == {"id": waise["id"]}


def test_importiertes_asset_wird_als_neu_gekennzeichnet(
    client: TestClient, governance, anmelden, rolle_geben
) -> None:
    plattform = anmelden("Plattform")
    rolle_geben(plattform.user_id, "plattform", "global")
    client.post(
        "/api/v1/import/assets",
        json={
            "quelle": "zentrale-entwicklungsplattform",
            "datensaetze": [{"typ": "tool", "externe_id": "T-1", "name": "Frisch importiert"}],
        },
        headers=plattform.kopf,
    )
    treffer = zeile(client, governance, "assets_ohne_prozess")
    assert treffer["eintraege"][0]["hinweis"] == "neu importiert, noch nicht zugeordnet"


# --- Einzelne Zeilen ------------------------------------------------------


def test_prozesse_ohne_tragenden_owner(
    client: TestClient, governance, owner, vertretung, prozess_daten, db
) -> None:
    from app.models.organisation import User

    lege_prozess_an(client, owner, vertretung, prozess_daten, name="Mit Owner")
    ohne = lege_prozess_an(
        client,
        owner,
        vertretung,
        prozess_daten,
        name="Owner ohne Rolle",
        owner_user_id=vertretung.user_id,
    )
    treffer = zeile(client, governance, "prozesse_ohne_owner")
    assert [e["titel"] for e in treffer["eintraege"]] == ["Owner ohne Rolle"]
    assert treffer["eintraege"][0]["hinweis"] == "Owner ohne Rolle"
    assert treffer["eintraege"][0]["id"] == ohne["id"]

    # Ein deaktivierter Owner faellt ebenfalls auf.
    db.expire_all()
    db.query(User).filter(User.subject == "sub-owner").one().ist_aktiv = False
    db.commit()
    treffer = zeile(client, governance, "prozesse_ohne_owner")
    assert {e["hinweis"] for e in treffer["eintraege"]} == {
        "Owner ohne Rolle",
        "Owner deaktiviert",
    }


def test_non_compliant_je_stufe_und_filter(
    client: TestClient, governance, owner, vertretung, prozess_daten, db, attestieren, organisation
) -> None:
    from app.models.governance import Lenkungsvorgang
    from app.services import lenkung

    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    bewerte(client, owner, prozess["id"], ds=3)
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Auffaellig", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    attestieren(governance.kopf, tool["id"])
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    client.post(
        f"/api/v1/tools/{tool['id']}/compliance",
        json={"begruendung": "Abweichung beobachtet"},
        headers=governance.kopf,
    )

    treffer = zeile(client, governance, "non_compliant")
    assert treffer["anzahl"] == 1
    assert treffer["aggregat"]["je_stufe"] == {"1": 1}
    assert treffer["eintraege"][0]["ziel_modul"] == "lenkung"
    assert treffer["eintraege"][0]["ziel_filter"] == {"eskalationsstufe": "1"}

    db.expire_all()
    vorgang = db.query(Lenkungsvorgang).one()
    lenkung.eskaliere_faellige(db, vorgang.frist + timedelta(days=1))
    db.commit()

    nur_1 = zeile(client, governance, "non_compliant", "?eskalationsstufe=1")
    assert nur_1["anzahl"] == 0
    assert nur_1["aggregat"]["je_stufe"] == {"2": 1}
    nur_2 = zeile(client, governance, "non_compliant", "?eskalationsstufe=2")
    assert nur_2["anzahl"] == 1


def test_rahmenabweichungen_rechnen_statt_auf_eine_meldung_zu_warten(
    client: TestClient, governance, organisation, owner, prozess_daten, vertretung, attestieren
) -> None:
    """E-64: die Zeile zeigt die Lage, nicht die Meldebereitschaft.

    Vorher las sie den letzten gemeldeten Zustand — ein Werkzeug ohne Meldung
    fehlte darin, auch wenn seine Abweichung messbar war.
    """
    prozess = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    ).json()
    client.post(
        "/api/v1/tools",
        json={"name": "Ohne Kante", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    )
    sauber = client.post(
        "/api/v1/tools",
        json={"name": "Sauber", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    attestieren(governance.kopf, sauber["id"])
    client.post(
        f"/api/v1/tools/{sauber['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )

    # Niemand hat etwas gemeldet — und trotzdem steht das eine in der Zeile.
    treffer = zeile(client, governance, "rahmenabweichungen")
    assert [e["titel"] for e in treffer["eintraege"]] == ["Ohne Kante"]
    assert treffer["eintraege"][0]["hinweis"].startswith("gelb")

    # Eine Meldung macht aus Gelb Rot, und der Grund steht daneben.
    client.post(
        f"/api/v1/tools/{sauber['id']}/compliance",
        json={"begruendung": "Zugriff außerhalb des Rahmens"},
        headers=governance.kopf,
    )
    titel = [e["titel"] for e in zeile(client, governance, "rahmenabweichungen")["eintraege"]]
    assert sorted(titel) == ["Ohne Kante", "Sauber"]


def test_kritikalitaetsketten_zeigen_nur_geerbte_faelle(
    client: TestClient, governance, owner, vertretung, prozess_daten
) -> None:
    nachfolger = lege_prozess_an(
        client, owner, vertretung, prozess_daten, name="Zahlungslauf", ausfallfolge="kritisch"
    )
    lege_prozess_an(
        client,
        owner,
        vertretung,
        prozess_daten,
        name="Erfassung",
        ausfallfolge="gering",
        nachgelagert_ids=[nachfolger["id"]],
    )
    treffer = zeile(client, governance, "kritikalitaetsketten")
    assert [e["titel"] for e in treffer["eintraege"]] == ["Erfassung"]
    assert "Zahlungslauf" in treffer["eintraege"][0]["hinweis"]


def test_tier_verteilung_je_technologie_und_monat(
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren, organisation
) -> None:
    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    bewertung = bewerte(client, owner, prozess["id"], ds=3)
    tool = client.post(
        "/api/v1/tools",
        json={
            "name": "Skript",
            "technologie": "apps-script",
            "organisationseinheit_id": organisation["fin_de"],
        },
        headers=governance.kopf,
    ).json()
    attestieren(governance.kopf, tool["id"])
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    client.post(
        "/api/v1/tools",
        json={"name": "Ohne Prozess", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    )

    treffer = zeile(client, governance, "tier_verteilung")
    assert treffer["aggregat"]["je_technologie"] == {"apps-script": {"3": 1}}
    monat = bewertung["bewertet_am"][:7]
    assert treffer["aggregat"]["je_monat"] == {monat: {"3": 1}}


def test_inaktive_assets(client: TestClient, governance, db, organisation) -> None:
    from app.models.governance import ToolObjekt

    aktiv = client.post(
        "/api/v1/tools",
        json={"name": "Aktiv", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    alt = client.post(
        "/api/v1/tools",
        json={"name": "Alt", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    db.expire_all()
    import uuid as uuid_modul

    db.get(ToolObjekt, uuid_modul.UUID(aktiv["id"])).letzte_aktivitaet_am = datetime.now(UTC)
    db.get(ToolObjekt, uuid_modul.UUID(alt["id"])).letzte_aktivitaet_am = datetime.now(
        UTC
    ) - timedelta(days=400)
    db.commit()

    treffer = zeile(client, governance, "inaktive_assets")
    assert [e["titel"] for e in treffer["eintraege"]] == ["Alt"]
    assert "letzte Aktivität" in treffer["eintraege"][0]["hinweis"]


def test_stillgelegtes_asset_gilt_als_inaktiv(
    client: TestClient, governance, owner, vertretung, prozess_daten, attestieren, organisation
) -> None:
    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    bewerte(client, owner, prozess["id"], ds=1)
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Stillgelegt", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    attestieren(governance.kopf, tool["id"])
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    vorgang = client.post(
        f"/api/v1/tools/{tool['id']}/compliance",
        json={"begruendung": "Abweichung beobachtet"},
        headers=governance.kopf,
    ).json()["lenkungsvorgang"]
    client.post(
        f"/api/v1/lenkungsvorgaenge/{vorgang['id']}/aufloesung",
        json={"art": "stilllegen"},
        headers=governance.kopf,
    )
    treffer = zeile(client, governance, "inaktive_assets")
    assert [e["hinweis"] for e in treffer["eintraege"]] == ["stillgelegt"]


def test_ueberfaellige_selbstverpflichtungen(
    client: TestClient, governance, owner, vertretung, prozess_daten, db
) -> None:
    from app.models.governance import Selbstverpflichtung

    prozess = lege_prozess_an(client, owner, vertretung, prozess_daten)
    bewerte(client, owner, prozess["id"], ds=3)
    client.post(
        "/api/v1/selbstverpflichtungen",
        json={
            "typ": "prozesseigner",
            "prozessobjekt_id": prozess["id"],
            "aussagen": {i: {"bestaetigt": True, "kommentar": ""} for i in P_AUSSAGEN},
        },
        headers=owner.kopf,
    )
    assert zeile(client, governance, "ueberfaellige_selbstverpflichtungen")["anzahl"] == 0

    db.expire_all()
    eintrag = db.query(Selbstverpflichtung).one()
    eintrag.gueltig_bis = datetime.now(UTC) - timedelta(days=1)
    db.commit()

    treffer = zeile(client, governance, "ueberfaellige_selbstverpflichtungen")
    assert [e["titel"] for e in treffer["eintraege"]] == [prozess["name"]]
    assert treffer["eintraege"][0]["ziel_modul"] == "prozesse"


def test_ueberfaellige_selbstverpflichtung_eines_tools(
    client: TestClient, governance, db, organisation
) -> None:
    from app.models.governance import Selbstverpflichtung

    tool = client.post(
        "/api/v1/tools",
        json={"name": "Tool mit Frist", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    client.post(
        "/api/v1/selbstverpflichtungen",
        json={
            "typ": "technischer_owner",
            "tool_objekt_id": tool["id"],
            "aussagen": {i: {"bestaetigt": True, "kommentar": ""} for i in T_AUSSAGEN},
        },
        headers=governance.kopf,
    )
    db.expire_all()
    eintrag = db.query(Selbstverpflichtung).one()
    eintrag.gueltig_bis = datetime.now(UTC) - timedelta(days=1)
    db.commit()

    treffer = zeile(client, governance, "ueberfaellige_selbstverpflichtungen")
    assert [e["titel"] for e in treffer["eintraege"]] == ["Tool mit Frist"]
    assert treffer["eintraege"][0]["ziel_modul"] == "tools"


def test_widerspruch_zwischen_erklaerung_und_zustand(
    client: TestClient, governance, organisation
) -> None:
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Widerspruch", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    client.post(
        f"/api/v1/tools/{tool['id']}/compliance",
        json={"begruendung": "Abweichung beobachtet"},
        headers=governance.kopf,
    )
    # Noch keine Erklaerung: kein Widerspruch.
    assert zeile(client, governance, "widersprueche")["anzahl"] == 0

    client.post(
        "/api/v1/selbstverpflichtungen",
        json={
            "typ": "technischer_owner",
            "tool_objekt_id": tool["id"],
            "aussagen": {i: {"bestaetigt": True, "kommentar": ""} for i in T_AUSSAGEN},
        },
        headers=governance.kopf,
    )
    treffer = zeile(client, governance, "widersprueche")
    assert [e["titel"] for e in treffer["eintraege"]] == ["Widerspruch"]
    assert (
        treffer["eintraege"][0]["hinweis"] == f"{AUSSAGE_RAHMEN_EINGEHALTEN} bestätigt, Zustand rot"
    )


def test_verneinte_aussage_ist_kein_widerspruch(
    client: TestClient, governance, organisation
) -> None:
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Ehrlich", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    client.post(
        f"/api/v1/tools/{tool['id']}/compliance",
        json={"begruendung": "Abweichung beobachtet"},
        headers=governance.kopf,
    )
    aussagen = {i: {"bestaetigt": True, "kommentar": ""} for i in T_AUSSAGEN}
    aussagen[AUSSAGE_RAHMEN_EINGEHALTEN] = {
        "bestaetigt": False,
        "kommentar": "Rahmen aktuell verlassen",
    }
    client.post(
        "/api/v1/selbstverpflichtungen",
        json={"typ": "technischer_owner", "tool_objekt_id": tool["id"], "aussagen": aussagen},
        headers=governance.kopf,
    )
    assert zeile(client, governance, "widersprueche")["anzahl"] == 0


# --- Abnahmekriterium 6.3: Sichtbarkeit ----------------------------------


def test_land_scope_sieht_nur_den_eigenen_bereich(
    client: TestClient,
    governance,
    owner,
    vertretung,
    prozess_daten,
    anmelden,
    rolle_geben,
    organisation,
) -> None:
    lege_prozess_an(
        client,
        owner,
        vertretung,
        prozess_daten,
        name="Nur DE",
        owner_user_id=vertretung.user_id,
        umsetzung_land_org_ids=[organisation["fin_de"]],
    )
    lege_prozess_an(
        client,
        owner,
        vertretung,
        prozess_daten,
        name="Nur FR",
        owner_user_id=vertretung.user_id,
        umsetzung_land_org_ids=[organisation["fin_fr"]],
    )

    de_nutzer = anmelden("Sicht DE")
    rolle_geben(
        de_nutzer.user_id, "prozess_umsetzer", "organisationseinheit", organisation["fin_de"]
    )
    eigene = zeile(client, de_nutzer, "prozesse_ohne_owner")
    assert [e["titel"] for e in eigene["eintraege"]] == ["Nur DE"]

    global_sicht = zeile(client, governance, "prozesse_ohne_owner")
    assert {e["titel"] for e in global_sicht["eintraege"]} == {"Nur DE", "Nur FR"}


def test_fachbereichsfilter(
    client: TestClient, governance, owner, vertretung, prozess_daten, organisation
) -> None:
    lege_prozess_an(
        client,
        owner,
        vertretung,
        prozess_daten,
        name="Finance-Prozess",
        owner_user_id=vertretung.user_id,
    )
    finance = zeile(
        client,
        governance,
        "prozesse_ohne_owner",
        f"?fachbereich_id={organisation['fachbereich_finance']}",
    )
    assert finance["anzahl"] == 1
    hr = zeile(
        client,
        governance,
        "prozesse_ohne_owner",
        f"?fachbereich_id={organisation['fachbereich_hr']}",
    )
    assert hr["anzahl"] == 0


def test_uebersicht_beachtet_den_fachbereichsfilter(
    client: TestClient, governance, owner, vertretung, prozess_daten, organisation
) -> None:
    lege_prozess_an(client, owner, vertretung, prozess_daten, owner_user_id=vertretung.user_id)
    uebersicht = client.get(
        f"/api/v1/cockpit?fachbereich_id={organisation['fachbereich_hr']}",
        headers=governance.kopf,
    ).json()
    je_zeile = {z["schluessel"]: z["anzahl"] for z in uebersicht}
    assert je_zeile["prozesse_ohne_owner"] == 0


def test_ohne_rolle_ist_das_cockpit_leer(
    client: TestClient, anmelden, governance, organisation
) -> None:
    client.post(
        "/api/v1/tools",
        json={"name": "Unsichtbar", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    )
    fremder = anmelden("Ohne Rolle")
    uebersicht = client.get("/api/v1/cockpit", headers=fremder.kopf).json()
    assert all(z["anzahl"] == 0 for z in uebersicht)


def test_cockpit_verlangt_anmeldung(client: TestClient) -> None:
    assert client.get("/api/v1/cockpit").status_code == 401


# --- Alt-Anwendungen im Melde-/Blockierungspfad (Leitdokument A.16) --------


@pytest.fixture
def altanwendung(client: TestClient, governance, db):
    """Ein vorgefundenes Tool-Objekt, wie es der Sync anlegt."""
    from datetime import timedelta

    from app.models.governance import ToolObjekt

    def _anlegen(name: str, *, alter_tage: int = 0, status: str = "importiert_unbestaetigt"):
        tool = ToolObjekt(
            name=name,
            herkunft="importiert",
            quelle="sync-test",
            externe_id=f"ext-{name}",
            status=status,
        )
        db.add(tool)
        db.flush()
        if alter_tage:
            tool.erstellt_am = datetime.now(UTC) - timedelta(days=alter_tage)
        db.commit()
        return tool

    return _anlegen


def test_unbestaetigte_altanwendung_steht_im_meldepfad(
    client: TestClient, governance, altanwendung
) -> None:
    tool = altanwendung("Vorgefunden A")
    eintraege = zeile(client, governance, "altanwendungen")["eintraege"]
    treffer = next(e for e in eintraege if e["id"] == str(tool.id))
    assert "Meldepfad" in treffer["hinweis"]
    assert "noch nicht bestätigt" in treffer["hinweis"]
    assert treffer["ziel_modul"] == "tools"


def test_abgelaufene_meldefrist_wechselt_in_den_blockierungspfad(
    client: TestClient, governance, altanwendung
) -> None:
    tool = altanwendung("Vorgefunden B", alter_tage=200)
    eintraege = zeile(client, governance, "altanwendungen")["eintraege"]
    treffer = next(e for e in eintraege if e["id"] == str(tool.id))
    assert "Blockierungspfad" in treffer["hinweis"]


def test_bestaetigte_altanwendung_ohne_prozess_bleibt_im_pfad(
    client: TestClient, governance, altanwendung
) -> None:
    tool = altanwendung("Vorgefunden C", status="bestaetigt")
    eintraege = zeile(client, governance, "altanwendungen")["eintraege"]
    treffer = next(e for e in eintraege if e["id"] == str(tool.id))
    assert "keinem Prozessobjekt zugeordnet" in treffer["hinweis"]


def test_selbst_angelegtes_tool_ist_keine_altanwendung(
    client: TestClient, governance, organisation
) -> None:
    """Wer sein Tool anmeldet, hat den Weg nicht vor sich — er ist ihn gegangen."""
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Selbst gemeldet", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    eintraege = zeile(client, governance, "altanwendungen")["eintraege"]
    assert not any(e["id"] == tool["id"] for e in eintraege)


def test_vollstaendig_gefuehrte_altanwendung_verlaesst_den_pfad(
    client: TestClient, governance, owner, vertretung, prozess_daten, altanwendung, attestieren
) -> None:
    tool = altanwendung("Vorgefunden D", status="bestaetigt")
    prozess = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    ).json()
    client.post(
        f"/api/v1/prozesse/{prozess['id']}/bewertungen",
        json=nutzlast(profil_von()),
        headers=owner.kopf,
    )
    attestieren(governance.kopf, str(tool.id))
    client.post(
        f"/api/v1/tools/{tool.id}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    eintraege = zeile(client, governance, "altanwendungen")["eintraege"]
    assert not any(e["id"] == str(tool.id) for e in eintraege)
