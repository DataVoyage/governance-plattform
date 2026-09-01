"""Governance-Query-API — Abnahmekriterien Phase 7 (Architektur 7.3)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.test_bewertung import antworten_fuer, profil_von

#: Passt zu GP_QUERY_API_SERVICE_TOKENS aus der Testumgebung.
SERVICE_KOPF = {"X-Service-Token": "service-token-1"}


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


@pytest.fixture
def prozess(client: TestClient, owner, vertretung, prozess_daten):
    return client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    ).json()


def bewerte(client: TestClient, anmeldung, prozess_id: str, **profil):
    return client.post(
        f"/api/v1/prozesse/{prozess_id}/bewertungen",
        json={"modus": "vollstaendig", "antworten": antworten_fuer(profil_von(**profil))},
        headers=anmeldung.kopf,
    ).json()["bewertung"]


def frage(client: TestClient, pfad: str, kopf: dict | None = None):
    return client.get(f"/api/v1/query{pfad}", headers=SERVICE_KOPF if kopf is None else kopf)


# --- Abnahmekriterium 7.2: Service-Authentifizierung ---------------------


@pytest.mark.parametrize(
    "pfad",
    [
        "/prozess/00000000-0000-0000-0000-000000000000/tier",
        "/prozess/00000000-0000-0000-0000-000000000000/k-klassen",
        "/tool/00000000-0000-0000-0000-000000000000/erlaubnisrahmen",
        "/changes",
    ],
)
def test_ohne_service_token_wird_abgewiesen(client: TestClient, pfad: str) -> None:
    assert client.get(f"/api/v1/query{pfad}").status_code == 401
    assert frage(client, pfad, {"X-Service-Token": "falsch"}).status_code == 401


def test_nutzer_token_genuegt_nicht(client: TestClient, governance) -> None:
    """Eine andockende Anwendung ist keine Person (Architektur 10.3)."""
    assert frage(client, "/changes", governance.kopf).status_code == 401


# --- Abnahmekriterium 7.1: dieselbe Fachlogik wie im Wizard --------------


def test_tier_und_profil_entsprechen_dem_wizard(client: TestClient, owner, prozess) -> None:
    vorschau = client.post(
        f"/api/v1/prozesse/{prozess['id']}/bewertung/wizard",
        json={
            "modus": "vollstaendig",
            "antworten": antworten_fuer(profil_von(ds=3, mb=1, it=1, rg=2, ur=2)),
        },
        headers=owner.kopf,
    ).json()["vorschau"]
    bewerte(client, owner, prozess["id"], ds=3, mb=1, it=1, rg=2, ur=2)

    antwort = frage(client, f"/prozess/{prozess['id']}/tier")
    assert antwort.status_code == 200
    assert antwort.json()["tier"] == vorschau["tier"]
    assert antwort.json()["profil"] == vorschau["profil"]


def test_k_klassen_entsprechen_dem_wizard(client: TestClient, owner, prozess) -> None:
    bewertung = bewerte(client, owner, prozess["id"], ds=3, mb=1, it=1, rg=2, ur=2)
    antwort = frage(client, f"/prozess/{prozess['id']}/k-klassen")
    assert antwort.status_code == 200
    assert antwort.json()["ausgeloest"] == bewertung["ausgeloeste_k_klassen"]
    assert antwort.json()["ausgeloest"] == [
        "K1",
        "K2",
        "K3",
        "K4",
        "K5",
        "K7",
        "K8",
        "K9",
    ]


def test_k_klassen_auch_nach_schnellem_durchlauf(client: TestClient, owner, prozess) -> None:
    """Die schnelle Variante speichert keine K-Klassen — die API leitet sie ab."""
    client.post(
        f"/api/v1/prozesse/{prozess['id']}/bewertungen",
        json={"modus": "schnell", "antworten": antworten_fuer(profil_von(ds=3))},
        headers=owner.kopf,
    )
    antwort = frage(client, f"/prozess/{prozess['id']}/k-klassen")
    assert antwort.json()["ausgeloest"] == ["K1", "K2", "K3", "K4", "K5"]


def test_neubewertung_schlaegt_sofort_durch(client: TestClient, owner, prozess) -> None:
    bewerte(client, owner, prozess["id"], ds=1)
    assert frage(client, f"/prozess/{prozess['id']}/tier").json()["tier"] == 1
    bewerte(client, owner, prozess["id"], ds=3)
    assert frage(client, f"/prozess/{prozess['id']}/tier").json()["tier"] == 3


def test_ohne_bewertung_gibt_es_keine_auskunft(client: TestClient, prozess) -> None:
    antwort = frage(client, f"/prozess/{prozess['id']}/tier")
    assert antwort.status_code == 404


def test_unbekanntes_prozessobjekt(client: TestClient) -> None:
    antwort = frage(client, "/prozess/00000000-0000-0000-0000-000000000000/tier")
    assert antwort.status_code == 404


# --- Erlaubnisrahmen ------------------------------------------------------


def test_erlaubnisrahmen_vereinigt_die_prozesskanten(
    client: TestClient, governance, owner, vertretung, prozess_daten
) -> None:
    kreditoren = client.post(
        "/api/v1/datenobjekte", json={"name": "Kreditorenstamm"}, headers=governance.kopf
    ).json()
    buchungen = client.post(
        "/api/v1/datenobjekte", json={"name": "Buchungen"}, headers=governance.kopf
    ).json()

    eng = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(
            owner.user_id,
            vertretung.user_id,
            name="Eng",
            customer="team",
            input_datenobjekt_ids=[kreditoren["id"]],
        ),
        headers=owner.kopf,
    ).json()
    weit = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(
            owner.user_id,
            vertretung.user_id,
            name="Weit",
            customer="extern",
            input_datenobjekt_ids=[buchungen["id"]],
        ),
        headers=owner.kopf,
    ).json()
    bewerte(client, owner, weit["id"], ds=3)
    client.patch(
        f"/api/v1/prozesse/{weit['id']}",
        json={"erlaubte_externe_ziele": ["sftp.partner.example", "api.partner.example"]},
        headers=owner.kopf,
    )

    tool = client.post("/api/v1/tools", json={"name": "Gemeinsam"}, headers=governance.kopf).json()
    for prozessobjekt in (eng, weit):
        client.post(
            f"/api/v1/tools/{tool['id']}/prozesse",
            json={"prozessobjekt_id": prozessobjekt["id"]},
            headers=governance.kopf,
        )

    rahmen = frage(client, f"/tool/{tool['id']}/erlaubnisrahmen").json()
    assert {d["name"] for d in rahmen["erlaubte_datenobjekte"]} == {
        "Kreditorenstamm",
        "Buchungen",
    }
    # Reichweite: das Maximum beider Kanten.
    assert rahmen["erlaubte_reichweite"] == "extern"
    assert rahmen["erlaubte_externe_ziele"] == [
        "api.partner.example",
        "sftp.partner.example",
    ]
    assert rahmen["tier"] == 3
    assert set(rahmen["quelle_prozess_ids"]) == {eng["id"], weit["id"]}


def test_erlaubnisrahmen_ohne_prozesskante(client: TestClient, governance) -> None:
    tool = client.post("/api/v1/tools", json={"name": "Frei"}, headers=governance.kopf).json()
    rahmen = frage(client, f"/tool/{tool['id']}/erlaubnisrahmen").json()
    assert rahmen == {
        "erlaubte_datenobjekte": [],
        "erlaubte_reichweite": None,
        "erlaubte_externe_ziele": [],
        "tier": None,
        "quelle_prozess_ids": [],
    }


def test_unbekanntes_tool(client: TestClient) -> None:
    antwort = frage(client, "/tool/00000000-0000-0000-0000-000000000000/erlaubnisrahmen")
    assert antwort.status_code == 404


def test_die_api_provisioniert_nichts(client: TestClient) -> None:
    """Nur Auskunft: die Query-API kennt ausschliesslich GET."""
    spezifikation = client.app.openapi()
    query_pfade = {p: ops for p, ops in spezifikation["paths"].items() if "/query/" in p}
    assert query_pfade
    for ops in query_pfade.values():
        assert set(ops) == {"get"}


# --- Abnahmekriterium 7.4: Delta-Abfrage ---------------------------------


def test_delta_liefert_lueckenlos_und_in_reihenfolge(
    client: TestClient, governance, owner, prozess
) -> None:
    """Abnahmekriterium 7.4."""
    start = frage(client, "/changes").json()
    ab = start["naechster_cursor"]

    bewerte(client, owner, prozess["id"], ds=1)
    client.post("/api/v1/tools", json={"name": "Neu"}, headers=governance.kopf)
    bewerte(client, owner, prozess["id"], ds=3)

    delta = frage(client, f"/changes?since={ab}").json()
    cursors = [c["cursor"] for c in delta["changes"]]
    assert cursors == sorted(cursors)
    assert len(cursors) == len(set(cursors))
    assert all(c >= ab for c in cursors)
    assert delta["naechster_cursor"] == cursors[-1] + 1

    typen = [c["entity_type"] for c in delta["changes"]]
    assert typen.count("bewertung") == 2
    assert "tool" in typen


def test_derselbe_cursor_liefert_dasselbe(client: TestClient, owner, prozess) -> None:
    """Nachweis der Zustandslosigkeit des Cursors."""
    bewerte(client, owner, prozess["id"], ds=1)
    erste = frage(client, "/changes?since=0").json()
    zweite = frage(client, "/changes?since=0").json()
    assert erste == zweite


def test_delta_filtert_nach_entity_type(client: TestClient, governance, owner, prozess) -> None:
    bewerte(client, owner, prozess["id"], ds=1)
    client.post("/api/v1/tools", json={"name": "Nur Tool"}, headers=governance.kopf)

    nur_tools = frage(client, "/changes?since=0&entity_type=tool").json()
    assert {c["entity_type"] for c in nur_tools["changes"]} == {"tool"}

    beide = frage(client, "/changes?since=0&entity_type=tool&entity_type=bewertung").json()
    assert {c["entity_type"] for c in beide["changes"]} == {"tool", "bewertung"}


def test_delta_lehnt_unbekannten_typ_ab(client: TestClient) -> None:
    antwort = frage(client, "/changes?since=0&entity_type=irgendwas")
    assert antwort.status_code == 404


def test_delta_ohne_aenderungen_bleibt_am_cursor(client: TestClient) -> None:
    aktuell = frage(client, "/changes").json()["naechster_cursor"]
    leer = frage(client, f"/changes?since={aktuell}").json()
    assert leer["changes"] == []
    assert leer["naechster_cursor"] == aktuell


def test_delta_begrenzt_die_menge(client: TestClient, owner, prozess) -> None:
    for _ in range(3):
        bewerte(client, owner, prozess["id"], ds=1)
    begrenzt = frage(client, "/changes?since=0&limit=2").json()
    assert len(begrenzt["changes"]) == 2
    # Der naechste Lauf setzt lueckenlos fort: der gelieferte Cursor geht
    # unveraendert wieder hinein.
    fortsetzung = frage(client, f"/changes?since={begrenzt['naechster_cursor']}").json()
    assert fortsetzung["changes"][0]["cursor"] == begrenzt["changes"][-1]["cursor"] + 1


# --- Abnahmekriterium 7.3: Dokumentation und Probeintegration ------------


def test_openapi_dokumentiert_die_vier_endpunkte(client: TestClient) -> None:
    spezifikation = client.app.openapi()
    pfade = {p for p in spezifikation["paths"] if p.startswith("/api/v1/query")}
    assert pfade == {
        "/api/v1/query/prozess/{prozess_id}/tier",
        "/api/v1/query/prozess/{prozess_id}/k-klassen",
        "/api/v1/query/tool/{tool_id}/erlaubnisrahmen",
        "/api/v1/query/changes",
    }
    for pfad in pfade:
        beschreibung = spezifikation["paths"][pfad]["get"]
        assert beschreibung["summary"]
        assert beschreibung["description"]
        assert "200" in beschreibung["responses"]

    schemata = spezifikation["components"]["schemas"]
    assert "example" in schemata["TierAus"]
    assert "example" in schemata["ErlaubnisrahmenAus"]


def test_probeintegration_mit_platzhalter_client(
    client: TestClient, governance, owner, prozess
) -> None:
    """Ein andockender Client, der nur der Dokumentation folgt.

    Er meldet sich mit einem Service-Token an, holt Tier und K-Klassen, fragt
    den Rahmen des Tools ab und merkt sich den Cursor fuer den naechsten Lauf —
    genau der Ablauf, den Architektur 7.3 beschreibt.
    """
    bewerte(client, owner, prozess["id"], ds=3, ur=2)
    tool = client.post(
        "/api/v1/tools", json={"name": "Andocker-Tool"}, headers=governance.kopf
    ).json()
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )

    class PlatzhalterClient:
        """Minimaler Client — kennt nur die vier dokumentierten Routen."""

        def __init__(self, http: TestClient, token: str) -> None:
            self.http = http
            self.kopf = {"X-Service-Token": token}
            self.cursor = 0

        def _get(self, pfad: str) -> dict:
            antwort = self.http.get(f"/api/v1/query{pfad}", headers=self.kopf)
            antwort.raise_for_status()
            return antwort.json()

        def darf_provisionieren(self, prozess_id: str, tool_id: str) -> dict:
            tier = self._get(f"/prozess/{prozess_id}/tier")
            klassen = self._get(f"/prozess/{prozess_id}/k-klassen")
            rahmen = self._get(f"/tool/{tool_id}/erlaubnisrahmen")
            return {"tier": tier["tier"], "klassen": klassen["ausgeloest"], "rahmen": rahmen}

        def hole_neues(self) -> list[dict]:
            antwort = self._get(f"/changes?since={self.cursor}")
            self.cursor = antwort["naechster_cursor"]
            return antwort["changes"]

    andocker = PlatzhalterClient(client, "service-token-1")
    auskunft = andocker.darf_provisionieren(prozess["id"], tool["id"])
    assert auskunft["tier"] == 3
    assert "K9" in auskunft["klassen"]
    assert auskunft["rahmen"]["tier"] == 3

    erste_runde = andocker.hole_neues()
    assert erste_runde
    assert andocker.hole_neues() == []

    bewerte(client, owner, prozess["id"], ds=1)
    zweite_runde = andocker.hole_neues()
    assert [c["entity_type"] for c in zweite_runde] == ["bewertung"]


def test_service_name_kommt_aus_der_konfiguration(client: TestClient) -> None:
    from app.config import get_settings

    assert get_settings().service_token_map == {"service-token-1": "self-service-frontend"}
