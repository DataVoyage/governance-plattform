"""Selbstverpflichtung — Abnahmekriterien AP-5 (Leitdokument A.10).

Gepruefte Zusagen: der Katalog sagt, was A.10.2 und A.10.3 sagen; die Erklaerung
haengt an der Bewertung und nicht nur an einem Datum; bei Tier 1 genuegt die
Kurzform; ab Tier 3 verlaengert ein Klick.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.services import selbstverpflichtung as sv
from tests.test_bewertung import nutzlast, profil_von

PE = [a.id for a in sv.AUSSAGEN_PROZESSEIGNER]
TO = [a.id for a in sv.AUSSAGEN_TECHNISCHER_OWNER]


def bestaetigt(ids: list[str]) -> dict[str, dict]:
    return {i: {"bestaetigt": True, "kommentar": ""} for i in ids}


@pytest.fixture
def owner(anmelden, rolle_geben, organisation):
    nutzer = anmelden("Prozess-Owner", subject="sub-owner")
    rolle_geben(nutzer.user_id, "prozess_owner", "organisationseinheit", organisation["fin_int"])
    rolle_geben(nutzer.user_id, "governance", "global")
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


def bewerte(client: TestClient, anmeldung, prozess_id: str, **profil) -> dict:
    antwort = client.post(
        f"/api/v1/prozesse/{prozess_id}/bewertungen",
        json=nutzlast(profil_von(**profil)),
        headers=anmeldung.kopf,
    )
    assert antwort.status_code == 201, antwort.text
    return antwort.json()["bewertung"]


def gib_ab(client: TestClient, anmeldung, prozess_id: str, aussagen=None):
    return client.post(
        "/api/v1/selbstverpflichtungen",
        json={
            "typ": "prozesseigner",
            "prozessobjekt_id": prozess_id,
            "aussagen": aussagen if aussagen is not None else bestaetigt(PE),
        },
        headers=anmeldung.kopf,
    )


def deckung(client: TestClient, anmeldung, prozess_id: str) -> dict:
    antwort = client.get(
        f"/api/v1/prozesse/{prozess_id}/selbstverpflichtung", headers=anmeldung.kopf
    )
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


# --- Der Katalog (A.10.2, A.10.3) ----------------------------------------


def test_katalog_traegt_die_sechs_aussagen_je_typ(client: TestClient, owner) -> None:
    katalog = client.get("/api/v1/selbstverpflichtungen/katalog", headers=owner.kopf).json()
    je_typ = {k["typ"]: k for k in katalog}
    assert [a["id"] for a in je_typ["prozesseigner"]["aussagen"]] == PE
    assert [a["id"] for a in je_typ["technischer_owner"]["aussagen"]] == TO
    assert je_typ["prozesseigner"]["version"] == sv.KATALOG_VERSION


def test_die_aussagen_sind_spezifisch_und_nicht_pauschal() -> None:
    """A.10.4: „nach bestem Wissen" ist ausdruecklich ausgeschlossen."""
    alle = [a.text for a in sv.AUSSAGEN_PROZESSEIGNER + sv.AUSSAGEN_TECHNISCHER_OWNER]
    for text in alle:
        assert "bestem Wissen" not in text
        assert len(text) > 40, f"Zu unbestimmt: {text}"


def test_die_prozesseigner_aussagen_decken_a_10_2_ab() -> None:
    """Die sechs Punkte aus A.10.2, an ihren Schluesselbegriffen erkannt."""
    texte = {a.id: a.text for a in sv.AUSSAGEN_PROZESSEIGNER}
    assert "Zweck" in texte["PE1"]
    assert "Datenobjekte" in texte["PE2"]
    assert "Empfängerkreis" in texte["PE3"]
    assert "Kontrolle einzelner Beschäftigter" in texte["PE4"]
    assert "Aufbewahrungspflichten" in texte["PE5"]
    assert "Änderung des Zwecks" in texte["PE6"]


def test_schicht_2_verbote_stehen_nicht_im_katalog() -> None:
    """A.13.2 Schicht 2 wird durchgesetzt, nicht erklaert (siehe AP-6)."""
    texte = " ".join(a.text for a in sv.AUSSAGEN_TECHNISCHER_OWNER)
    assert "Unternehmensidentität" not in texte
    assert "Zugangsdaten" not in texte


# --- Kurzform bei Tier 1 (A.10.5) ----------------------------------------


def test_tier_1_verlangt_nur_die_kurzform(client: TestClient, owner, prozess) -> None:
    bewerte(client, owner, prozess["id"])  # alles verneint -> Tier 1
    kurz = [a.id for a in sv.verlangte_aussagen("prozesseigner", 1)]
    assert kurz == ["PE1", "PE2", "PE6"]

    stand = deckung(client, owner, prozess["id"])
    assert stand["tier"] == 1
    assert stand["verlangte_aussagen"] == kurz

    antwort = gib_ab(client, owner, prozess["id"], bestaetigt(kurz))
    assert antwort.status_code == 201, antwort.text
    assert antwort.json()["vollstaendig"] is True
    assert deckung(client, owner, prozess["id"])["gedeckt"] is True


def test_ab_tier_2_wird_der_ganze_katalog_verlangt(client: TestClient, owner, prozess) -> None:
    bewerte(client, owner, prozess["id"], ds=2)
    stand = deckung(client, owner, prozess["id"])
    assert stand["tier"] == 2
    assert stand["verlangte_aussagen"] == PE

    # Die Kurzform genuegt jetzt nicht mehr.
    kurz = gib_ab(client, owner, prozess["id"], bestaetigt(["PE1", "PE2", "PE6"]))
    assert kurz.status_code == 201
    assert kurz.json()["vollstaendig"] is False
    stand = deckung(client, owner, prozess["id"])
    assert stand["gedeckt"] is False
    assert stand["grund"] == "unvollstaendig"


def test_ohne_bewertung_gilt_die_kurzform(client: TestClient, owner, prozess) -> None:
    stand = deckung(client, owner, prozess["id"])
    assert stand["tier"] is None
    assert stand["verlangte_aussagen"] == ["PE1", "PE2", "PE6"]


# --- Bindung an die Bewertung (A.10.4) -----------------------------------


def test_die_erklaerung_wird_an_die_bewertung_gebunden(client: TestClient, owner, prozess) -> None:
    bewertung = bewerte(client, owner, prozess["id"], ds=3)
    eintrag = gib_ab(client, owner, prozess["id"]).json()
    assert eintrag["bewertung_id"] == bewertung["id"]
    assert eintrag["tier_bei_abgabe"] == 3
    assert eintrag["katalog_version"] == sv.KATALOG_VERSION


def test_eine_neubewertung_entwertet_die_erklaerung(client: TestClient, owner, prozess) -> None:
    """Abnahme AP-5: nach Neubewertung erscheint die Erklaerung als verfallen."""
    bewerte(client, owner, prozess["id"], ds=3)
    gib_ab(client, owner, prozess["id"])
    assert deckung(client, owner, prozess["id"])["gedeckt"] is True

    bewerte(client, owner, prozess["id"], ds=3, mb=3)
    stand = deckung(client, owner, prozess["id"])
    assert stand["gedeckt"] is False
    assert stand["grund"] == "profil_veraltet"
    assert "A.10.4" in stand["grundtext"]
    # Die Erklaerung selbst bleibt erhalten und lesbar.
    assert stand["aktuelle"]["vollstaendig"] is True


def test_verfallene_erklaerung_blockiert_die_aktivierung(
    client: TestClient, owner, prozess
) -> None:
    bewerte(client, owner, prozess["id"], ds=3)
    gib_ab(client, owner, prozess["id"])
    client.post(
        f"/api/v1/prozesse/{prozess['id']}/gates",
        json={"gate_typ": "1", "begruendung": "Erstfreigabe"},
        headers=owner.kopf,
    )
    offen = client.get("/api/v1/gates", headers=owner.kopf).json()
    client.post(
        f"/api/v1/gates/{offen[0]['id']}/entscheidung",
        json={"status": "freigegeben", "kommentar": "In Ordnung"},
        headers=owner.kopf,
    )
    assert (
        client.patch(
            f"/api/v1/prozesse/{prozess['id']}", json={"status": "aktiv"}, headers=owner.kopf
        ).status_code
        == 200
    )

    # Zurueck in den Entwurf, neu bewerten — die Erklaerung traegt nicht mehr.
    client.patch(
        f"/api/v1/prozesse/{prozess['id']}", json={"status": "entwurf"}, headers=owner.kopf
    )
    bewerte(client, owner, prozess["id"], ds=3, ur=2)
    verweigert = client.patch(
        f"/api/v1/prozesse/{prozess['id']}", json={"status": "aktiv"}, headers=owner.kopf
    )
    assert verweigert.status_code == 422
    assert "Selbstverpflichtung" in verweigert.json()["detail"]


def test_erklaerung_nach_altem_katalog_zaehlt_nicht(client: TestClient, owner, prozess, db) -> None:
    """E-32: Zustimmung zu Text A ist keine Zustimmung zu Text B."""
    from app.models.governance import Selbstverpflichtung

    bewerte(client, owner, prozess["id"], ds=3)
    eintrag_id = gib_ab(client, owner, prozess["id"]).json()["id"]
    db.expire_all()
    eintrag = db.get(Selbstverpflichtung, uuid.UUID(eintrag_id))
    eintrag.katalog_version = 1
    db.commit()

    stand = deckung(client, owner, prozess["id"])
    assert stand["gedeckt"] is False
    assert stand["grund"] == "alter_katalog"


# --- Jahresbestaetigung ab Tier 3 ----------------------------------------


def test_ein_klick_verlaengert_die_erklaerung(client: TestClient, owner, prozess, db) -> None:
    from app.models.governance import Selbstverpflichtung

    bewerte(client, owner, prozess["id"], ds=3)
    erste = gib_ab(client, owner, prozess["id"]).json()
    assert erste["gueltig_bis"] is not None

    db.expire_all()
    eintrag = db.get(Selbstverpflichtung, uuid.UUID(erste["id"]))
    eintrag.gueltig_bis = datetime.now(UTC) - timedelta(days=1)
    db.commit()
    assert deckung(client, owner, prozess["id"])["grund"] == "frist_abgelaufen"

    antwort = client.post(
        f"/api/v1/selbstverpflichtungen/{erste['id']}/bestaetigung", headers=owner.kopf
    )
    assert antwort.status_code == 200, antwort.text
    zweite = antwort.json()
    assert zweite["id"] != erste["id"]
    assert zweite["aussagen"] == erste["aussagen"]
    assert deckung(client, owner, prozess["id"])["gedeckt"] is True

    # Die alte Erklaerung bleibt in der Historie stehen.
    historie = client.get(
        f"/api/v1/prozesse/{prozess['id']}/selbstverpflichtungen", headers=owner.kopf
    ).json()
    assert [e["id"] for e in historie] == [zweite["id"], erste["id"]]


def test_eine_verfallene_erklaerung_laesst_sich_nicht_bestaetigen(
    client: TestClient, owner, prozess
) -> None:
    """Ein Klick ist zu wenig, wenn sich der Sachverhalt geaendert hat."""
    bewerte(client, owner, prozess["id"], ds=3)
    erste = gib_ab(client, owner, prozess["id"]).json()
    bewerte(client, owner, prozess["id"], ds=3, mb=3)

    antwort = client.post(
        f"/api/v1/selbstverpflichtungen/{erste['id']}/bestaetigung", headers=owner.kopf
    )
    assert antwort.status_code == 422
    assert "neu abzugeben" in antwort.json()["detail"]


# --- Der technische Owner am Tool-Objekt ---------------------------------


@pytest.fixture
def tool(client: TestClient, owner, prozess, attestieren, organisation):
    bewerte(client, owner, prozess["id"], ds=3)
    angelegt = client.post(
        "/api/v1/tools",
        json={
            "name": "Auswertung",
            "technischer_owner_user_id": owner.user_id,
            "organisationseinheit_id": organisation["fin_de"],
        },
        headers=owner.kopf,
    ).json()
    attestieren(owner.kopf, angelegt["id"])
    kante = client.post(
        f"/api/v1/tools/{angelegt['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=owner.kopf,
    )
    assert kante.status_code == 201, kante.text
    return angelegt


def tool_deckung(client: TestClient, anmeldung, tool_id: str) -> dict:
    antwort = client.get(
        f"/api/v1/tools/{tool_id}/selbstverpflichtung/deckung", headers=anmeldung.kopf
    )
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def test_der_technische_owner_erklaert_am_tool(client: TestClient, owner, tool) -> None:
    stand = tool_deckung(client, owner, tool["id"])
    assert stand["gedeckt"] is False
    assert stand["grund"] == "keine"
    assert stand["tier"] == 3
    assert stand["verlangte_aussagen"] == TO

    antwort = client.post(
        "/api/v1/selbstverpflichtungen",
        json={
            "typ": "technischer_owner",
            "tool_objekt_id": tool["id"],
            "aussagen": bestaetigt(TO),
        },
        headers=owner.kopf,
    )
    assert antwort.status_code == 201, antwort.text
    assert antwort.json()["tier_bei_abgabe"] == 3
    assert tool_deckung(client, owner, tool["id"])["gedeckt"] is True


def test_ein_gestiegenes_tier_entwertet_die_tool_erklaerung(
    client: TestClient, owner, vertretung, prozess_daten, attestieren, organisation
) -> None:
    """Das Gegenstueck zur Profilbindung fuer geerbte Einstufungen."""
    niedrig = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id, name="Niedrig"),
        headers=owner.kopf,
    ).json()
    bewerte(client, owner, niedrig["id"])  # Tier 1
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Erbe", "organisationseinheit_id": organisation["fin_de"]},
        headers=owner.kopf,
    ).json()
    attestieren(owner.kopf, tool["id"])
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": niedrig["id"]},
        headers=owner.kopf,
    )
    # Tier 1 verlangt die Kurzform.
    kurz = [a.id for a in sv.verlangte_aussagen("technischer_owner", 1)]
    client.post(
        "/api/v1/selbstverpflichtungen",
        json={
            "typ": "technischer_owner",
            "tool_objekt_id": tool["id"],
            "aussagen": bestaetigt(kurz),
        },
        headers=owner.kopf,
    )
    assert tool_deckung(client, owner, tool["id"])["gedeckt"] is True

    # Ein zweiter, hoeher eingestufter Prozess hebt das geerbte Tier an.
    hoch = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id, name="Hoch"),
        headers=owner.kopf,
    ).json()
    bewerte(client, owner, hoch["id"], ds=3)
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": hoch["id"]},
        headers=owner.kopf,
    )
    stand = tool_deckung(client, owner, tool["id"])
    assert stand["gedeckt"] is False
    assert stand["grund"] == "tier_gestiegen"


# --- Kommentar je Aussage ------------------------------------------------


def test_der_kommentar_haengt_an_der_aussage(client: TestClient, owner, prozess) -> None:
    bewerte(client, owner, prozess["id"], ds=3)
    aussagen = bestaetigt(PE)
    aussagen["PE3"] = {"bestaetigt": True, "kommentar": "Empfaenger: Konzernrevision, sonst keine."}
    eintrag = gib_ab(client, owner, prozess["id"], aussagen).json()
    assert eintrag["aussagen"]["PE3"]["kommentar"].startswith("Empfaenger")
    assert eintrag["aussagen"]["PE1"]["kommentar"] == ""


# --- Gates: eine Ablehnung ist zu begruenden -----------------------------


def test_ablehnung_ohne_begruendung_wird_abgewiesen(client: TestClient, owner, prozess) -> None:
    client.post(
        f"/api/v1/prozesse/{prozess['id']}/gates",
        json={"gate_typ": "1", "begruendung": "Erstfreigabe"},
        headers=owner.kopf,
    )
    gate = client.get("/api/v1/gates", headers=owner.kopf).json()[0]

    ohne = client.post(
        f"/api/v1/gates/{gate['id']}/entscheidung",
        json={"status": "abgelehnt", "kommentar": "   "},
        headers=owner.kopf,
    )
    assert ohne.status_code == 422
    assert "begründen" in ohne.json()["detail"]

    mit = client.post(
        f"/api/v1/gates/{gate['id']}/entscheidung",
        json={"status": "abgelehnt", "kommentar": "Reichweite ist unklar."},
        headers=owner.kopf,
    )
    assert mit.status_code == 200
    assert mit.json()["entscheidungskommentar"] == "Reichweite ist unklar."


def test_freigabe_braucht_keine_begruendung(client: TestClient, owner, prozess) -> None:
    client.post(
        f"/api/v1/prozesse/{prozess['id']}/gates",
        json={"gate_typ": "1", "begruendung": "Erstfreigabe"},
        headers=owner.kopf,
    )
    gate = client.get("/api/v1/gates", headers=owner.kopf).json()[0]
    antwort = client.post(
        f"/api/v1/gates/{gate['id']}/entscheidung",
        json={"status": "freigegeben"},
        headers=owner.kopf,
    )
    assert antwort.status_code == 200


# --- Cockpit -------------------------------------------------------------


def zeile(client: TestClient, anmeldung, schluessel: str) -> dict:
    antwort = client.get(f"/api/v1/cockpit/{schluessel}", headers=anmeldung.kopf)
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def test_verfallene_erklaerung_erscheint_im_cockpit(client: TestClient, owner, prozess) -> None:
    bewerte(client, owner, prozess["id"], ds=3)
    gib_ab(client, owner, prozess["id"])
    assert zeile(client, owner, "ueberfaellige_selbstverpflichtungen")["anzahl"] == 0

    bewerte(client, owner, prozess["id"], ds=3, mb=3)
    treffer = zeile(client, owner, "ueberfaellige_selbstverpflichtungen")
    eintraege = [e for e in treffer["eintraege"] if e["id"] == prozess["id"]]
    assert len(eintraege) == 1
    assert "überholten Bewertung" in eintraege[0]["hinweis"]


def test_tier_1_ohne_erklaerung_ist_kein_befund(client: TestClient, owner, prozess) -> None:
    """Erst ab Tier 3 ist die Erklaerung Aktivierungsbedingung."""
    bewerte(client, owner, prozess["id"])
    treffer = zeile(client, owner, "ueberfaellige_selbstverpflichtungen")
    assert [e for e in treffer["eintraege"] if e["id"] == prozess["id"]] == []


def test_alte_attestierung_erscheint_im_cockpit(
    client: TestClient, owner, db, organisation
) -> None:
    from app.models.governance import ToolObjekt

    tool = client.post(
        "/api/v1/tools",
        json={"name": "Alt", "organisationseinheit_id": organisation["fin_de"]},
        headers=owner.kopf,
    ).json()
    client.put(
        f"/api/v1/tools/{tool['id']}/attestierungen",
        json={
            "attest_entscheidung_ueber_personen": False,
            "attest_mensch_dazwischen": True,
            "attest_undeklarierte_quellen": False,
        },
        headers=owner.kopf,
    )
    assert zeile(client, owner, "attestierungen_veraltet")["anzahl"] == 0

    db.expire_all()
    eintrag = db.get(ToolObjekt, uuid.UUID(tool["id"]))
    eintrag.attestiert_am = datetime.now(UTC) - timedelta(days=400)
    db.commit()

    treffer = zeile(client, owner, "attestierungen_veraltet")
    assert [e["titel"] for e in treffer["eintraege"]] == ["Alt"]
    assert treffer["eintraege"][0]["ziel_modul"] == "tools"


def test_ein_nie_attestiertes_tool_ist_hier_kein_befund(
    client: TestClient, owner, organisation
) -> None:
    """Fehlende Attestierung ist eine andere Zeile — hier geht es ums Alter."""
    client.post(
        "/api/v1/tools",
        json={"name": "Nie attestiert", "organisationseinheit_id": organisation["fin_de"]},
        headers=owner.kopf,
    )
    assert zeile(client, owner, "attestierungen_veraltet")["anzahl"] == 0
