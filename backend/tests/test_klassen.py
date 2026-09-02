"""Anforderungsklassen und Technologiematrix (Leitdokument A.9, AP-7).

Geprueft wird die zweite Uebersetzungsstufe aus A.9.1: vom ausgeloesten
K-Code zu einer Entscheidung ueber die eingesetzte Technologie.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services import bewertung as bewertung_service
from app.services import klassen as klassen_service
from tests.test_bewertung import nutzlast, profil_von


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
def techniker(anmelden, rolle_geben, organisation):
    nutzer = anmelden("Technischer Owner", subject="sub-technik")
    rolle_geben(nutzer.user_id, "technischer_owner", "organisationseinheit", organisation["fin_de"])
    return nutzer


@pytest.fixture
def aufbau(
    client: TestClient, governance, owner, techniker, organisation, prozess_daten, attestieren
):
    """Ein bewertetes Prozessobjekt mit einem Tool bestimmter Technologie."""

    def _aufbau(technologie: str | None = "apps-script", **profil) -> dict:
        prozess = client.post(
            "/api/v1/prozesse",
            json=prozess_daten(owner.user_id, techniker.user_id),
            headers=owner.kopf,
        ).json()
        antwort = client.post(
            f"/api/v1/prozesse/{prozess['id']}/bewertungen",
            json=nutzlast(profil_von(**profil)),
            headers=owner.kopf,
        )
        assert antwort.status_code == 201, antwort.text
        tool = client.post(
            "/api/v1/tools",
            json={
                "name": "Rechnungs-Skript",
                "technologie": technologie,
                "organisationseinheit_id": organisation["fin_de"],
                "technischer_owner_user_id": techniker.user_id,
            },
            headers=governance.kopf,
        ).json()
        attestieren(governance.kopf, tool["id"])
        kante = client.post(
            f"/api/v1/tools/{tool['id']}/prozesse",
            json={"prozessobjekt_id": prozess["id"]},
            headers=governance.kopf,
        )
        assert kante.status_code == 201, kante.text
        return {"prozess": prozess, "tool": tool, "bewertung": antwort.json()["bewertung"]}

    return _aufbau


def befund(client: TestClient, anmeldung, tool_id: str) -> dict:
    antwort = client.get(f"/api/v1/tools/{tool_id}/klassenbefund", headers=anmeldung.kopf)
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def arten(inhalt: dict) -> dict[str, str]:
    return {e["k_klasse"]: e["art"] for e in inhalt["befunde"]}


# --- Die Klassen selbst (A.9.2) ------------------------------------------


def test_alle_zehn_klassen_mit_name_zweck_und_ausloeser(client: TestClient, governance) -> None:
    liste = client.get("/api/v1/anforderungsklassen", headers=governance.kopf).json()
    assert [k["schluessel"] for k in liste] == [f"K{n}" for n in range(1, 11)]
    for klasse in liste:
        assert len(klasse["name"]) > 5
        assert len(klasse["zweck"]) > 20
        assert len(klasse["ausloeser"]) > 5


#: Je Klasse ein Profil, das sie ausloest, und eines, das sie nicht ausloest.
#: Damit haengt der Ausloesertext aus ``klassen.py`` an derselben Wahrheit wie
#: die Rechnung in ``bewertung.leite_k_klassen_ab`` — ein Text, der davon
#: abdriftet, faellt hier auf.
PROFILE: dict[str, tuple[dict, dict | None]] = {
    "K1": ({"ki": 0, "ds": 0, "mb": 0, "it": 0, "rg": 0, "ur": 0}, None),
    "K2": ({"ki": 0, "ds": 0, "mb": 0, "it": 0, "rg": 0, "ur": 0}, None),
    "K3": ({"it": 2}, {"it": 1}),
    "K4": ({"ds": 3}, {"ds": 2}),
    "K5": ({"ds": 2}, {"ds": 1, "it": 1}),
    "K6": ({"ki": 1}, {"ki": 0}),
    "K7": ({"mb": 1}, {"mb": 0}),
    "K8": ({"rg": 2}, {"rg": 1}),
    "K9": ({"ur": 2}, {"ur": 1}),
    "K10": ({"it": 3}, {"it": 2}),
}


@pytest.mark.parametrize("klasse", list(PROFILE))
def test_ausloeserbedingung_passt_zur_rechnung(klasse: str) -> None:
    ausloesend, nicht = PROFILE[klasse]
    leer = {"ki": 0, "ds": 0, "mb": 0, "it": 0, "rg": 0, "ur": 0}
    assert klasse in bewertung_service.leite_k_klassen_ab({**leer, **ausloesend})
    if nicht is not None:
        assert klasse not in bewertung_service.leite_k_klassen_ab({**leer, **nicht})


# --- Matrix (Teil C.1) ----------------------------------------------------


def test_matrix_deckt_jede_technologie_und_jede_klasse_ab(client: TestClient, governance) -> None:
    matrix = client.get("/api/v1/technologiematrix", headers=governance.kopf).json()
    technologien = {e["technologie"] for e in matrix}
    assert technologien == set(klassen_service.TECHNOLOGIEN)
    assert len(matrix) == len(klassen_service.TECHNOLOGIEN) * 10
    # Jedes Feld traegt einen Satz — eine Farbe ohne Begruendung ist keine
    # Entscheidungsgrundlage.
    assert all(len(e["begruendung"]) > 20 for e in matrix)


def test_organisatorische_klassen_sind_ueberall_erfuellt(client: TestClient, governance) -> None:
    """Keine Technologie hindert daran, den Betriebsrat zu beteiligen."""
    matrix = client.get("/api/v1/technologiematrix", headers=governance.kopf).json()
    organisatorisch = {"K1", "K2", "K3", "K4", "K6", "K7", "K10"}
    for eintrag in matrix:
        if eintrag["k_klasse"] in organisatorisch:
            assert eintrag["bewertung"] == "erfuellt", eintrag


def test_technologien_kommen_aus_einer_liste(client: TestClient, governance) -> None:
    liste = client.get("/api/v1/technologien", headers=governance.kopf).json()
    assert [t["schluessel"] for t in liste] == list(klassen_service.TECHNOLOGIEN)


def test_governance_pflegt_die_matrix(client: TestClient, governance, aufbau) -> None:
    """V-KLA-03: die Änderung ist sofort in den Befunden wirksam."""
    daten = aufbau("python-kubernetes", ur=2)
    assert arten(befund(client, governance, daten["tool"]["id"]))["K9"] == "erfuellt"

    antwort = client.put(
        "/api/v1/technologiematrix/python-kubernetes/K9",
        json={"bewertung": "nicht_erfuellbar", "begruendung": "Kein Ausweichbetrieb vorgesehen."},
        headers=governance.kopf,
    )
    assert antwort.status_code == 200
    assert arten(befund(client, governance, daten["tool"]["id"]))["K9"] == "ausschluss"


def test_matrixfeld_ohne_begruendung_wird_abgewiesen(client: TestClient, governance) -> None:
    antwort = client.put(
        "/api/v1/technologiematrix/apps-script/K5",
        json={"bewertung": "erfuellt", "begruendung": "   "},
        headers=governance.kopf,
    )
    assert antwort.status_code == 422
    assert "begründen" in antwort.json()["detail"]


def test_nur_governance_pflegt_die_matrix(client: TestClient, techniker) -> None:
    antwort = client.put(
        "/api/v1/technologiematrix/apps-script/K5",
        json={"bewertung": "erfuellt", "begruendung": "Passt schon."},
        headers=techniker.kopf,
    )
    assert antwort.status_code == 403


def test_unbekannte_technologie_oder_klasse(client: TestClient, governance) -> None:
    for pfad in (
        "/api/v1/technologiematrix/gibt-es-nicht/K5",
        "/api/v1/technologiematrix/apps-script/K99",
    ):
        antwort = client.put(
            pfad,
            json={"bewertung": "erfuellt", "begruendung": "Egal."},
            headers=governance.kopf,
        )
        assert antwort.status_code == 404


# --- Abgleich (A.9.3) -----------------------------------------------------


def test_ohne_prozesskante_gibt_es_nichts_abzugleichen(client: TestClient, governance) -> None:
    tool = client.post(
        "/api/v1/tools", json={"name": "Frei", "technologie": "appsheet"}, headers=governance.kopf
    ).json()
    inhalt = befund(client, governance, tool["id"])
    assert inhalt["k_klassen"] == []
    assert inhalt["befunde"] == []
    assert inhalt["ausschluss"] is False


def test_ausschluss_bei_nicht_erfuellbarer_klasse(client: TestClient, governance, aufbau) -> None:
    """V-KLA-04 und die Abnahme von AP-7: AppSheet trägt K5 nicht."""
    daten = aufbau("appsheet", ds=3)
    inhalt = befund(client, governance, daten["tool"]["id"])
    assert "K5" in inhalt["k_klassen"]
    assert arten(inhalt)["K5"] == "ausschluss"
    assert inhalt["ausschluss"] is True
    eintrag = next(e for e in inhalt["befunde"] if e["k_klasse"] == "K5")
    assert "Freigabemodell" in eintrag["begruendung"]


def test_kompensierbar_bleibt_offen_ohne_massnahme(client: TestClient, governance, aufbau) -> None:
    """V-KLA-05: ohne Kompensationsvermerk bleibt der Befund offen."""
    daten = aufbau("apps-script", ds=2)
    inhalt = befund(client, governance, daten["tool"]["id"])
    assert arten(inhalt)["K5"] == "kompensation_fehlt"
    assert inhalt["offen"] >= 1


def test_dokumentierte_kompensation_schliesst_den_befund(
    client: TestClient, governance, techniker, aufbau
) -> None:
    daten = aufbau("apps-script", ds=2)
    antwort = client.put(
        f"/api/v1/tools/{daten['tool']['id']}/kompensationen/K5",
        json={"massnahme": "Zugriff über die Rechte der angesprochenen Ablage geregelt."},
        headers=techniker.kopf,
    )
    assert antwort.status_code == 200, antwort.text

    inhalt = befund(client, governance, daten["tool"]["id"])
    assert arten(inhalt)["K5"] == "kompensiert"
    eintrag = next(e for e in inhalt["befunde"] if e["k_klasse"] == "K5")
    assert eintrag["massnahme"].startswith("Zugriff über")
    assert eintrag["offen"] is False


def test_kompensation_ohne_text_wird_abgewiesen(client: TestClient, techniker, aufbau) -> None:
    daten = aufbau("apps-script", ds=2)
    antwort = client.put(
        f"/api/v1/tools/{daten['tool']['id']}/kompensationen/K5",
        json={"massnahme": "   "},
        headers=techniker.kopf,
    )
    assert antwort.status_code == 422


def test_ausschluss_laesst_sich_nicht_wegkompensieren(
    client: TestClient, techniker, aufbau
) -> None:
    """Eine Kompensation auf einem Ausschluss wäre eine Umgehung des Kriteriums."""
    daten = aufbau("appsheet", ds=3)
    antwort = client.put(
        f"/api/v1/tools/{daten['tool']['id']}/kompensationen/K5",
        json={"massnahme": "Wir passen auf."},
        headers=techniker.kopf,
    )
    assert antwort.status_code == 422
    assert "Ausschluss" in antwort.json()["detail"]


def test_erfuellte_klasse_braucht_keine_kompensation(client: TestClient, techniker, aufbau) -> None:
    daten = aufbau("apps-script", ds=2)
    antwort = client.put(
        f"/api/v1/tools/{daten['tool']['id']}/kompensationen/K1",
        json={"massnahme": "Unnötig."},
        headers=techniker.kopf,
    )
    assert antwort.status_code == 422


def test_kompensation_wird_aktualisiert_statt_verdoppelt(
    client: TestClient, governance, techniker, aufbau
) -> None:
    daten = aufbau("apps-script", ds=2)
    pfad = f"/api/v1/tools/{daten['tool']['id']}/kompensationen/K5"
    erste = client.put(pfad, json={"massnahme": "Erster Stand."}, headers=techniker.kopf).json()
    zweite = client.put(pfad, json={"massnahme": "Zweiter Stand."}, headers=techniker.kopf).json()
    assert erste["id"] == zweite["id"]
    eintrag = next(
        e
        for e in befund(client, governance, daten["tool"]["id"])["befunde"]
        if e["k_klasse"] == "K5"
    )
    assert eintrag["massnahme"] == "Zweiter Stand."


def test_ohne_technologie_ist_jede_klasse_ungeprueft(
    client: TestClient, governance, aufbau
) -> None:
    """Eine fehlende Angabe ist kein Nachweis."""
    daten = aufbau(None, ds=3)
    inhalt = befund(client, governance, daten["tool"]["id"])
    assert set(arten(inhalt).values()) == {"ungeprueft"}
    assert inhalt["offen"] == len(inhalt["k_klassen"])


def test_kompensation_ohne_technologie_wird_abgewiesen(
    client: TestClient, techniker, aufbau
) -> None:
    daten = aufbau(None, ds=2)
    antwort = client.put(
        f"/api/v1/tools/{daten['tool']['id']}/kompensationen/K5",
        json={"massnahme": "Geht nicht."},
        headers=techniker.kopf,
    )
    assert antwort.status_code == 404


def test_prozessbefund_nennt_jedes_tool(client: TestClient, owner, aufbau) -> None:
    daten = aufbau("appsheet", ds=3)
    liste = client.get(
        f"/api/v1/prozesse/{daten['prozess']['id']}/klassenbefund", headers=owner.kopf
    ).json()
    assert len(liste) == 1
    assert liste[0]["tool_name"] == "Rechnungs-Skript"
    assert liste[0]["ausschluss"] is True


def test_fremder_sieht_keinen_befund(client: TestClient, anmelden, aufbau) -> None:
    daten = aufbau("appsheet", ds=3)
    fremder = anmelden("Ohne Rolle")
    assert (
        client.get(
            f"/api/v1/tools/{daten['tool']['id']}/klassenbefund", headers=fremder.kopf
        ).status_code
        == 403
    )


# --- Cockpit --------------------------------------------------------------


def test_cockpit_zeigt_den_ausschluss(client: TestClient, governance, aufbau) -> None:
    """Abnahme AP-7: der Fall erscheint am Tool und im Cockpit."""
    daten = aufbau("appsheet", ds=3)
    zeile = client.get(
        "/api/v1/cockpit/technologie_erfuellt_klasse_nicht", headers=governance.kopf
    ).json()
    treffer = [e for e in zeile["eintraege"] if e["id"] == daten["tool"]["id"]]
    assert treffer, zeile
    assert any("K5" in e["hinweis"] and "Ausschluss" in e["hinweis"] for e in treffer)
    assert all(e["ziel_modul"] == "tools" for e in treffer)


def test_cockpit_zeigt_kompensierte_faelle_nicht_mehr(
    client: TestClient, governance, techniker, aufbau
) -> None:
    daten = aufbau("apps-script", ds=2)
    zuvor = client.get(
        "/api/v1/cockpit/technologie_erfuellt_klasse_nicht", headers=governance.kopf
    ).json()
    assert any(e["id"] == daten["tool"]["id"] and "K5" in e["hinweis"] for e in zuvor["eintraege"])

    client.put(
        f"/api/v1/tools/{daten['tool']['id']}/kompensationen/K5",
        json={"massnahme": "Ablagerechte geregelt."},
        headers=techniker.kopf,
    )
    danach = client.get(
        "/api/v1/cockpit/technologie_erfuellt_klasse_nicht", headers=governance.kopf
    ).json()
    assert not any(
        e["id"] == daten["tool"]["id"] and "K5" in e["hinweis"] for e in danach["eintraege"]
    )


def test_cockpit_uebersicht_kennt_die_zeile(client: TestClient, governance) -> None:
    schluessel = [
        z["schluessel"] for z in client.get("/api/v1/cockpit", headers=governance.kopf).json()
    ]
    assert "technologie_erfuellt_klasse_nicht" in schluessel
