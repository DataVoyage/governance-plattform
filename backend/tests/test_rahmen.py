"""Erlaubnisrahmen nach Leitdokument A.13.2 — Schicht 1 und Schicht 2 (AP-6).

Geprueft wird beides: dass der Rahmen die sieben Elemente vollstaendig
abdeckt, und dass er neben jedes erlaubte Element das gemessene stellt. Ein
Rahmen ohne Messung ist eine Behauptung; erst der Vergleich macht eine
Abweichung sichtbar.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.test_bewertung import nutzlast, profil_von
from tests.test_query_api import SERVICE_KOPF


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
def datenobjekt(client: TestClient, governance, organisation):
    """Ein Baukasten fuer Datenobjekte einer bestimmten Kategorie."""

    def _anlegen(name: str, kategorie: str | None = "intern") -> dict:
        antwort = client.post(
            "/api/v1/datenobjekte",
            json={
                "name": name,
                "kategorie": kategorie,
                "fachbereich_id": organisation["fachbereich_finance"],
            },
            headers=governance.kopf,
        )
        assert antwort.status_code == 201, antwort.text
        return antwort.json()

    return _anlegen


@pytest.fixture
def prozess(client: TestClient, owner, anmelden, prozess_daten):
    vertretung = anmelden("Stellvertretung", subject="sub-vertretung")

    def _anlegen(**overrides) -> dict:
        antwort = client.post(
            "/api/v1/prozesse",
            json=prozess_daten(owner.user_id, vertretung.user_id, **overrides),
            headers=owner.kopf,
        )
        assert antwort.status_code == 201, antwort.text
        gelegt = antwort.json()
        client.post(
            f"/api/v1/prozesse/{gelegt['id']}/bewertungen",
            json=nutzlast(profil_von()),
            headers=owner.kopf,
        )
        return gelegt

    return _anlegen


@pytest.fixture
def tool(client: TestClient, governance, attestieren, organisation):
    def _anlegen(attest: dict | None = None, **felder) -> dict:
        angelegt = client.post(
            "/api/v1/tools",
            json={
                "name": "Rechnungs-Skript",
                **felder,
                "organisationseinheit_id": organisation["fin_de"],
            },
            headers=governance.kopf,
        ).json()
        attestieren(governance.kopf, angelegt["id"], **(attest or {}))
        return angelegt

    return _anlegen


def rahmen(client: TestClient, anmeldung, tool_id: str) -> dict:
    antwort = client.get(f"/api/v1/tools/{tool_id}/erlaubnisrahmen", headers=anmeldung.kopf)
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def element(antwort: dict, schluessel: str) -> dict:
    return next(e for e in antwort["elemente"] if e["schluessel"] == schluessel)


def verknuepfe(client: TestClient, governance, tool_id: str, prozess_id: str) -> None:
    antwort = client.post(
        f"/api/v1/tools/{tool_id}/prozesse",
        json={"prozessobjekt_id": prozess_id},
        headers=governance.kopf,
    )
    assert antwort.status_code == 201, antwort.text


# --- Schicht 1, Vollstaendigkeit -----------------------------------------


def test_rahmen_nennt_alle_sieben_elemente(client: TestClient, governance, tool) -> None:
    """B10: der Rahmen war zu drei Siebteln umgesetzt."""
    antwort = rahmen(client, governance, tool()["id"])
    assert [e["schluessel"] for e in antwort["elemente"]] == [
        "datenobjekte",
        "datenkategorie",
        "reichweite",
        "externe_ziele",
        "zugriffsart",
        "ausfuehrungsart",
        "ausfuehrungsidentitaet",
    ]


def test_ohne_prozesskante_ist_der_rahmen_leer(client: TestClient, governance, tool) -> None:
    """Positivlistenprinzip: was nicht erlaubt ist, ist nicht erlaubt."""
    antwort = rahmen(client, governance, tool()["id"])
    assert element(antwort, "datenobjekte")["erlaubt"] == []
    assert element(antwort, "datenkategorie")["erlaubt"] == []
    # Nichts erlaubt, aber auch nichts gemessen — das ist keine Abweichung.
    assert antwort["eingehalten"] is True


def test_reichweite_hat_keine_messung(client: TestClient, governance, tool, prozess) -> None:
    """Sie ist geerbt (A.4.4) und nach P1 nie eingegeben — es gibt nichts zu messen."""
    werkzeug = tool()
    verknuepfe(client, governance, werkzeug["id"], prozess()["id"])
    eintrag = element(rahmen(client, governance, werkzeug["id"]), "reichweite")
    assert eintrag["messbar"] is False
    assert eintrag["erlaubt"] == ["bereich"]
    assert eintrag["gemessen"] == []


# --- Obergrenze der Datenkategorie ---------------------------------------


def test_obergrenze_ist_die_hoechste_kategorie_im_rahmen(
    client: TestClient, governance, tool, prozess, datenobjekt
) -> None:
    offen = datenobjekt("Pressemitteilung", "oeffentlich")
    vertraulich = datenobjekt("Kalkulation", "vertraulich")
    werkzeug = tool()
    verknuepfe(
        client,
        governance,
        werkzeug["id"],
        prozess(input_datenobjekt_ids=[offen["id"], vertraulich["id"]])["id"],
    )
    assert element(rahmen(client, governance, werkzeug["id"]), "datenkategorie")["erlaubt"] == [
        "vertraulich"
    ]


def test_hoehere_kategorie_am_tool_ist_eine_abweichung(
    client: TestClient, governance, tool, prozess, datenobjekt
) -> None:
    """Der Fall, den A.4.6 „der Compliance am meisten wert" nennt."""
    intern = datenobjekt("Buchungsliste", "intern")
    personal = datenobjekt("Personalakte", "personenbezogen")
    werkzeug = tool()
    verknuepfe(
        client, governance, werkzeug["id"], prozess(input_datenobjekt_ids=[intern["id"]])["id"]
    )
    client.post(
        f"/api/v1/tools/{werkzeug['id']}/datenobjekte",
        json={"datenobjekt_id": personal["id"], "zugriffsart": "lesen"},
        headers=governance.kopf,
    )

    antwort = rahmen(client, governance, werkzeug["id"])
    kategorie = element(antwort, "datenkategorie")
    assert kategorie["erlaubt"] == ["intern"]
    assert kategorie["gemessen"] == ["personenbezogen"]
    assert kategorie["abweichung"] == ["personenbezogen"]
    assert element(antwort, "datenobjekte")["abweichung"] == ["Personalakte"]
    assert antwort["eingehalten"] is False


# --- Erlaubte Zugriffsart (A.4.1: die Output-Kante ist die Schreibkante) --


def test_ohne_output_datenobjekt_darf_nur_gelesen_werden(
    client: TestClient, governance, tool, prozess, datenobjekt
) -> None:
    objekt = datenobjekt("Buchungsliste")
    werkzeug = tool()
    verknuepfe(
        client, governance, werkzeug["id"], prozess(input_datenobjekt_ids=[objekt["id"]])["id"]
    )
    client.post(
        f"/api/v1/tools/{werkzeug['id']}/datenobjekte",
        json={"datenobjekt_id": objekt["id"], "zugriffsart": "lesen_schreiben"},
        headers=governance.kopf,
    )

    zugriff = element(rahmen(client, governance, werkzeug["id"]), "zugriffsart")
    assert zugriff["erlaubt"] == ["lesen"]
    assert zugriff["gemessen"] == ["lesen_schreiben"]
    assert zugriff["abweichung"] == ["Buchungsliste"]


def test_output_datenobjekt_erlaubt_den_schreibzugriff(
    client: TestClient, governance, tool, prozess, datenobjekt
) -> None:
    objekt = datenobjekt("Freigegebene Rechnung")
    werkzeug = tool()
    verknuepfe(
        client, governance, werkzeug["id"], prozess(output_datenobjekt_ids=[objekt["id"]])["id"]
    )
    client.post(
        f"/api/v1/tools/{werkzeug['id']}/datenobjekte",
        json={"datenobjekt_id": objekt["id"], "zugriffsart": "lesen_schreiben"},
        headers=governance.kopf,
    )

    zugriff = element(rahmen(client, governance, werkzeug["id"]), "zugriffsart")
    assert zugriff["erlaubt"] == ["lesen_schreiben"]
    assert zugriff["abweichung"] == []


# --- Erlaubte Ausfuehrungsart (zurueckgefuehrt auf Attestierung 2) --------


def test_mensch_dazwischen_deckt_jede_ausfuehrungsart(client: TestClient, governance, tool) -> None:
    werkzeug = tool(lauftyp="geplant")
    eintrag = element(rahmen(client, governance, werkzeug["id"]), "ausfuehrungsart")
    assert eintrag["erlaubt"] == ["interaktiv", "getriggert", "geplant"]
    assert eintrag["abweichung"] == []


def test_ohne_mensch_dazwischen_bleibt_nur_die_interaktive_ausfuehrung(
    client: TestClient, governance, tool
) -> None:
    werkzeug = tool(attest={"attest_mensch_dazwischen": False}, lauftyp="geplant")
    eintrag = element(rahmen(client, governance, werkzeug["id"]), "ausfuehrungsart")
    assert eintrag["erlaubt"] == ["interaktiv"]
    assert eintrag["gemessen"] == ["geplant"]
    assert eintrag["abweichung"] == ["geplant"]


def test_ohne_attestierung_deckt_der_rahmen_keine_ausfuehrungsart(
    client: TestClient, governance, organisation
) -> None:
    """Ohne Erklaerung ist nichts gedeckt — nicht alles."""
    ohne = client.post(
        "/api/v1/tools",
        json={
            "name": "Unerklaert",
            "lauftyp": "interaktiv",
            "organisationseinheit_id": organisation["fin_de"],
        },
        headers=governance.kopf,
    ).json()
    eintrag = element(rahmen(client, governance, ohne["id"]), "ausfuehrungsart")
    assert eintrag["erlaubt"] == []
    assert eintrag["abweichung"] == ["interaktiv"]


# --- Erlaubte Ausfuehrungsidentitaet -------------------------------------


def test_geplanter_lauf_verlangt_eine_benannte_dienstidentitaet(
    client: TestClient, governance, tool
) -> None:
    werkzeug = tool(lauftyp="geplant")
    client.patch(
        f"/api/v1/tools/{werkzeug['id']}",
        json={"ausfuehrungsidentitaet": "persoenlich"},
        headers=governance.kopf,
    )
    eintrag = element(rahmen(client, governance, werkzeug["id"]), "ausfuehrungsidentitaet")
    assert eintrag["erlaubt"] == ["benannter_dienst"]
    assert eintrag["abweichung"] == ["persoenlich"]


def test_interaktiver_lauf_laeuft_unter_der_person(client: TestClient, governance, tool) -> None:
    werkzeug = tool(lauftyp="interaktiv")
    client.patch(
        f"/api/v1/tools/{werkzeug['id']}",
        json={"ausfuehrungsidentitaet": "persoenlich"},
        headers=governance.kopf,
    )
    eintrag = element(rahmen(client, governance, werkzeug["id"]), "ausfuehrungsidentitaet")
    assert eintrag["erlaubt"] == ["persoenlich"]
    assert eintrag["abweichung"] == []


def test_ohne_lauftyp_bleiben_beide_identitaeten_offen(
    client: TestClient, governance, tool
) -> None:
    eintrag = element(rahmen(client, governance, tool()["id"]), "ausfuehrungsidentitaet")
    assert eintrag["erlaubt"] == ["persoenlich", "benannter_dienst"]


# --- Externe Ziele --------------------------------------------------------


def test_nicht_erklaertes_ziel_ist_eine_abweichung(
    client: TestClient, governance, tool, prozess
) -> None:
    werkzeug = tool()
    verknuepfe(
        client,
        governance,
        werkzeug["id"],
        prozess(erlaubte_externe_ziele=["sftp.partner.example"])["id"],
    )
    client.patch(
        f"/api/v1/tools/{werkzeug['id']}",
        json={"externe_ziele": ["sftp.partner.example", "unbekannt.example"]},
        headers=governance.kopf,
    )
    eintrag = element(rahmen(client, governance, werkzeug["id"]), "externe_ziele")
    assert eintrag["erlaubt"] == ["sftp.partner.example"]
    assert eintrag["abweichung"] == ["unbekannt.example"]


# --- Schicht 2 ------------------------------------------------------------


def test_geteiltes_konto_wird_selbst_erkannt(client: TestClient, governance, tool) -> None:
    werkzeug = tool()
    client.patch(
        f"/api/v1/tools/{werkzeug['id']}",
        json={"ausfuehrungsidentitaet": "geteiltes_konto"},
        headers=governance.kopf,
    )
    assert rahmen(client, governance, werkzeug["id"])["schicht2_befunde"] == ["identitaet_umgangen"]


def test_statische_zugangsdaten_werden_selbst_erkannt(client: TestClient, governance, tool) -> None:
    werkzeug = tool()
    client.patch(
        f"/api/v1/tools/{werkzeug['id']}",
        json={"statische_zugangsdaten": True},
        headers=governance.kopf,
    )
    assert rahmen(client, governance, werkzeug["id"])["schicht2_befunde"] == [
        "statische_zugangsdaten"
    ]


def test_die_beiden_erklaerten_verbote_kommen_zurueck(client: TestClient, governance, tool) -> None:
    """Was gespeichert wird, muss auch wieder herauskommen (E-64).

    Die Antwort des Tool-Endpunkts wird Feld fuer Feld gebaut. Ein neues Feld,
    das in der Datenbank steht und dort fehlt, laesst jeden Schalter in der
    Oberflaeche zurueckspringen: das PATCH gelingt, die Antwort sagt ``null``,
    und die Oberflaeche zeigt den alten Wert. Der Test prueft deshalb den
    Rueckweg, nicht nur die Wirkung.
    """
    werkzeug = tool()
    for feld, verbot in (
        ("protokollierung_umgangen", "protokollierung_umgangen"),
        ("daten_ins_offene_netz", "daten_ins_offene_netz"),
    ):
        antwort = client.patch(
            f"/api/v1/tools/{werkzeug['id']}", json={feld: True}, headers=governance.kopf
        )
        assert antwort.status_code == 200, antwort.text
        assert antwort.json()[feld] is True, f"{feld} fehlt in der Antwort"
        # Und beim naechsten Laden steht es immer noch da.
        gelesen = client.get(f"/api/v1/tools/{werkzeug['id']}", headers=governance.kopf).json()
        assert gelesen[feld] is True
        assert verbot in rahmen(client, governance, werkzeug["id"])["schicht2_befunde"]

        client.patch(f"/api/v1/tools/{werkzeug['id']}", json={feld: False}, headers=governance.kopf)
        assert (
            client.get(f"/api/v1/tools/{werkzeug['id']}", headers=governance.kopf).json()[feld]
            is False
        )


def test_jedes_aenderbare_feld_kommt_auch_zurueck(client: TestClient, governance, tool) -> None:
    """Die Gegenprobe als Regel, nicht als Einzelfall.

    ``ToolAendern`` sagt, was sich aendern laesst; ``ToolAus`` sagt, was
    herauskommt. Ein Feld, das nur in der ersten Liste steht, ist ein Schalter
    ohne Rueckmeldung — genau der Fehler, den E-64 hinterlassen hat.
    """
    from app.schemas.asset import ToolAendern, ToolAus

    aenderbar = set(ToolAendern.model_fields)
    sichtbar = set(ToolAus.model_fields)
    # ``metadaten`` und die Referenzfelder stehen bewusst nicht als Einzelwerte
    # in der Ausgabe; alles Uebrige muss zurueckkommen.
    fehlt = aenderbar - sichtbar
    assert not fehlt, f"aenderbar, aber nicht in der Antwort: {sorted(fehlt)}"
    del client, governance, tool


def test_entscheidung_ueber_personen_ohne_mensch_ist_ein_verbot(
    client: TestClient, governance, tool
) -> None:
    """Attestierung 1 und 2 zusammen ergeben den Fall, fuer den A.6 warnt."""
    werkzeug = tool(
        attest={
            "attest_entscheidung_ueber_personen": True,
            "attest_mensch_dazwischen": False,
        }
    )
    assert rahmen(client, governance, werkzeug["id"])["schicht2_befunde"] == [
        "entscheidung_ohne_mensch"
    ]


def test_entscheidung_mit_mensch_dazwischen_ist_keiner(
    client: TestClient, governance, tool
) -> None:
    werkzeug = tool(attest={"attest_entscheidung_ueber_personen": True})
    assert rahmen(client, governance, werkzeug["id"])["schicht2_befunde"] == []


def test_undeklarierte_quellen_sind_ein_verbot(client: TestClient, governance, tool) -> None:
    werkzeug = tool(attest={"attest_undeklarierte_quellen": True})
    assert rahmen(client, governance, werkzeug["id"])["schicht2_befunde"] == [
        "undeklarierte_quellen"
    ]


# --- Query-API (Architektur 7.3) -----------------------------------------


def test_query_api_liefert_alle_sieben_elemente(
    client: TestClient, governance, tool, prozess, datenobjekt
) -> None:
    objekt = datenobjekt("Freigegebene Rechnung", "vertraulich")
    werkzeug = tool(lauftyp="geplant")
    verknuepfe(
        client,
        governance,
        werkzeug["id"],
        prozess(output_datenobjekt_ids=[objekt["id"]], erlaubte_externe_ziele=["ziel.example"])[
            "id"
        ],
    )
    antwort = client.get(
        f"/api/v1/query/tool/{werkzeug['id']}/erlaubnisrahmen", headers=SERVICE_KOPF
    )
    assert antwort.status_code == 200, antwort.text
    inhalt = antwort.json()
    assert inhalt["obergrenze_datenkategorie"] == "vertraulich"
    assert inhalt["erlaubte_zugriffsart"] == "lesen_schreiben"
    assert inhalt["erlaubte_externe_ziele"] == ["ziel.example"]
    assert inhalt["erlaubte_ausfuehrungsarten"] == ["interaktiv", "getriggert", "geplant"]
    assert inhalt["erlaubte_ausfuehrungsidentitaeten"] == ["benannter_dienst"]
    # Die Auskunft sagt, was erlaubt ist — nicht, was gemessen wurde.
    assert "gemessen" not in inhalt
