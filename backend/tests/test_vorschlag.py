"""Vorschlagsdienst der Bewertung — Abnahmekriterien AP-4 (Leitdokument A.8.4).

Gepruefte Zusage: was aus vorhandenen Daten hervorgeht, wird nicht erfragt,
sondern vorgeschlagen — mit dem Objekt, aus dem der Vorschlag stammt. Und
umgekehrt: wo die Daten nichts hergeben, gibt es keinen Vorschlag, denn ein
geratener Vorschlag macht die Abweichung von ihm begruendungspflichtig.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.test_bewertung import abschliessen, antworten_fuer, nutzlast, profil_von, wizard


@pytest.fixture
def owner(anmelden, rolle_geben, organisation):
    nutzer = anmelden("Prozess-Owner", subject="sub-owner")
    rolle_geben(nutzer.user_id, "prozess_owner", "organisationseinheit", organisation["fin_int"])
    rolle_geben(nutzer.user_id, "datenobjekt_owner", "global")
    rolle_geben(nutzer.user_id, "governance", "global")
    return nutzer


@pytest.fixture
def vertretung(anmelden):
    return anmelden("Stellvertretung", subject="sub-vertretung")


@pytest.fixture
def datenobjekt(client: TestClient, owner, organisation):
    def _anlegen(name: str, kategorie: str | None) -> dict:
        antwort = client.post(
            "/api/v1/datenobjekte",
            json={
                "name": name,
                "kategorie": kategorie,
                "fachbereich_id": organisation["fachbereich_finance"],
            },
            headers=owner.kopf,
        )
        assert antwort.status_code == 201, antwort.text
        return antwort.json()

    return _anlegen


@pytest.fixture
def prozess_mit(client: TestClient, owner, vertretung, prozess_daten):
    """Ein Prozessobjekt mit frei gesetzten Feldern — die Datenlage des Falls."""

    def _anlegen(name: str = "Fall", **felder) -> dict:
        antwort = client.post(
            "/api/v1/prozesse",
            json=prozess_daten(owner.user_id, vertretung.user_id, name=name, **felder),
            headers=owner.kopf,
        )
        assert antwort.status_code == 201, antwort.text
        return antwort.json()

    return _anlegen


def frage_im_wizard(client: TestClient, anmeldung, prozess_id: str, bis: dict) -> dict:
    """Die naechste Frage samt Vorschlag, nach den bereits gegebenen Antworten."""
    antwort = wizard(client, anmeldung, prozess_id, bis)
    assert antwort.status_code == 200, antwort.text
    return antwort.json()["naechste_frage"]


# --- DS: aus Datenkategorien und Kundenkreis ------------------------------


def test_besondere_kategorie_schlaegt_ds_3_vor_und_nennt_das_objekt(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    """Abnahme AP-4: der Vorschlag nennt den Grund im Klartext, mit Quelle."""
    entgelt = datenobjekt("Entgeltdaten", "besondere_kategorie")
    prozess = prozess_mit(input_datenobjekt_ids=[entgelt["id"]])

    frage = frage_im_wizard(client, owner, prozess["id"], {"1a": False})
    assert frage["id"] == "2a"
    assert frage["vorschlag"] is True
    assert frage["belege"][0]["quelle"] == "datenobjekt"
    assert "Entgeltdaten" in frage["belege"][0]["text"]
    assert "besondere Kategorie" in frage["belege"][0]["text"]


def test_personenbezug_schlaegt_ds_2_vor(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    kontakt = datenobjekt("Kontaktdaten", "personenbezogen")
    prozess = prozess_mit(input_datenobjekt_ids=[kontakt["id"]])

    # 2a bleibt offen: die Profilbildungshaelfte steht in keinem Stammdatum.
    offen = frage_im_wizard(client, owner, prozess["id"], {"1a": False})
    assert offen["id"] == "2a"
    assert offen["vorschlag"] is None
    assert "Profilbildung" in offen["belege"][0]["text"]

    frage = frage_im_wizard(client, owner, prozess["id"], {"1a": False, "2a": False})
    assert frage["id"] == "2b"
    assert frage["vorschlag"] is True
    assert "Kontaktdaten" in frage["belege"][0]["text"]


def test_geschlossene_datenlage_ohne_personenbezug_schlaegt_nein_vor(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    buchungen = datenobjekt("Buchungen", "intern")
    prozess = prozess_mit(input_datenobjekt_ids=[buchungen["id"]])

    frage = frage_im_wizard(client, owner, prozess["id"], {"1a": False, "2a": False})
    assert frage["vorschlag"] is False
    assert "keines personenbezogen" in frage["belege"][0]["text"]


def test_ein_unkategorisiertes_objekt_verhindert_das_nein(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    """Ein noch nicht eingeordnetes Objekt kann alles sein — also kein „nein"."""
    buchungen = datenobjekt("Buchungen", "intern")
    unklar = datenobjekt("Noch offen", None)
    prozess = prozess_mit(input_datenobjekt_ids=[buchungen["id"], unklar["id"]])

    frage = frage_im_wizard(client, owner, prozess["id"], {"1a": False, "2a": False})
    assert frage["vorschlag"] is None
    assert "Noch offen" in frage["belege"][0]["text"]


def test_ohne_datenobjekte_gibt_es_nichts_abzuleiten(
    client: TestClient, owner, prozess_mit
) -> None:
    prozess = prozess_mit(input_datenobjekt_ids=[])
    frage = frage_im_wizard(client, owner, prozess["id"], {"1a": False, "2a": False})
    assert frage["vorschlag"] is None
    assert "kein Datenobjekt" in frage["belege"][0]["text"]


def test_externer_kundenkreis_haelt_ds_offen_statt_ja_zu_behaupten(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    """Der Kundenkreis wirkt nur negativ: er verhindert das „nein" (E-29)."""
    preisliste = datenobjekt("Preisliste", "oeffentlich")
    prozess = prozess_mit(customer="extern", input_datenobjekt_ids=[preisliste["id"]])

    frage = frage_im_wizard(client, owner, prozess["id"], {"1a": False, "2a": False})
    assert frage["vorschlag"] is None
    assert frage["belege"][0]["quelle"] == "kundenkreis"


def test_nur_oeffentliche_daten_schliessen_den_personenbezug_aus(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    preisliste = datenobjekt("Preisliste", "oeffentlich")
    prozess = prozess_mit(input_datenobjekt_ids=[preisliste["id"]])

    frage = frage_im_wizard(client, owner, prozess["id"], {"1a": False, "2a": False, "2b": False})
    assert frage["id"] == "2c"
    assert frage["vorschlag"] is False


def test_vertrauliche_daten_lassen_2c_offen(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    """„vertraulich" schliesst Personenbeziehbarkeit nicht aus."""
    vertraege = datenobjekt("Vertraege", "vertraulich")
    prozess = prozess_mit(input_datenobjekt_ids=[vertraege["id"]])

    frage = frage_im_wizard(client, owner, prozess["id"], {"1a": False, "2a": False, "2b": False})
    assert frage["id"] == "2c"
    assert frage["vorschlag"] is None


# --- MB: aus Kategorien und den Attestierungen nach A.6 -------------------


def test_besondere_kategorie_schlaegt_mitbestimmung_vor(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    entgelt = datenobjekt("Entgeltdaten", "besondere_kategorie")
    prozess = prozess_mit(input_datenobjekt_ids=[entgelt["id"]])

    frage = frage_im_wizard(client, owner, prozess["id"], {"1a": False, "2a": True})
    assert frage["id"] == "3a"
    assert frage["vorschlag"] is True
    assert "Leistungsbewertung" in frage["belege"][0]["text"]


def test_attestierung_1_traegt_den_mb_vorschlag(
    client: TestClient, owner, prozess_mit, datenobjekt, attestieren, organisation
) -> None:
    """A.6-Attestierung 1 ist die zweite Haelfte der Konjunktion aus A.5."""
    kontakt = datenobjekt("Bewerberdaten", "personenbezogen")
    prozess = prozess_mit(input_datenobjekt_ids=[kontakt["id"]])

    # Ohne Tool bleibt 3a offen: Personenbezug allein entscheidet nichts.
    vorher = frage_im_wizard(client, owner, prozess["id"], {"1a": False, "2a": False, "2b": True})
    assert vorher["id"] == "3a"
    assert vorher["vorschlag"] is None

    tool = client.post(
        "/api/v1/tools",
        json={"name": "Vorauswahl", "organisationseinheit_id": organisation["fin_de"]},
        headers=owner.kopf,
    ).json()
    attestieren(owner.kopf, tool["id"], attest_entscheidung_ueber_personen=True)
    verknuepft = client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=owner.kopf,
    )
    assert verknuepft.status_code == 201, verknuepft.text

    nachher = frage_im_wizard(client, owner, prozess["id"], {"1a": False, "2a": False, "2b": True})
    assert nachher["vorschlag"] is True
    assert nachher["belege"][-1]["quelle"] == "tool"
    assert "Vorauswahl" in nachher["belege"][-1]["text"]


def test_attestierung_2_traegt_den_vorschlag_zum_arbeitsablauf(
    client: TestClient, owner, prozess_mit, datenobjekt, attestieren, organisation
) -> None:
    buchungen = datenobjekt("Buchungen", "intern")
    prozess = prozess_mit(input_datenobjekt_ids=[buchungen["id"]])
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Autobucher", "organisationseinheit_id": organisation["fin_de"]},
        headers=owner.kopf,
    ).json()
    attestieren(owner.kopf, tool["id"], attest_mensch_dazwischen=False)
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=owner.kopf,
    )

    bis = {"1a": False, "2a": False, "2b": False, "2c": False, "3a": False}
    frage = frage_im_wizard(client, owner, prozess["id"], bis)
    # Ohne Personenbezug schlaegt 3b „nein" vor; danach kommt 3c.
    assert frage["id"] == "3b"
    assert frage["vorschlag"] is False

    dritte = frage_im_wizard(client, owner, prozess["id"], bis | {"3b": False})
    assert dritte["id"] == "3c"
    assert dritte["vorschlag"] is True
    assert "kein Mensch" in dritte["belege"][0]["text"]


# --- UR: aus Ausfallfolge und Prozesskette --------------------------------


def test_ausfallfolge_traegt_die_ur_dimension_vollstaendig(
    client: TestClient, owner, prozess_mit
) -> None:
    """Als einzige Dimension ist UR in beide Richtungen ableitbar."""
    prozess = prozess_mit(ausfallfolge="kritisch")
    bis = {"1a": False, "2a": False, "2b": False, "2c": False}
    bis |= {"3a": False, "3b": False, "3c": False}
    bis |= {"4a": False, "4b": False, "4c": False, "5a": False, "5b": False, "5c": False}

    frage = frage_im_wizard(client, owner, prozess["id"], bis)
    assert frage["id"] == "6a"
    assert frage["vorschlag"] is True
    assert "kritisch" in frage["belege"][0]["text"]


def test_geringe_ausfallfolge_verneint_die_oberen_stufen(
    client: TestClient, owner, prozess_mit
) -> None:
    prozess = prozess_mit(ausfallfolge="gering")
    bis = {"1a": False, "2a": False, "2b": False, "2c": False}
    bis |= {"3a": False, "3b": False, "3c": False}
    bis |= {"4a": False, "4b": False, "4c": False, "5a": False, "5b": False, "5c": False}

    assert frage_im_wizard(client, owner, prozess["id"], bis)["vorschlag"] is False
    zweite = frage_im_wizard(client, owner, prozess["id"], bis | {"6a": False})
    assert zweite["id"] == "6b"
    assert zweite["vorschlag"] is False
    dritte = frage_im_wizard(client, owner, prozess["id"], bis | {"6a": False, "6b": False})
    assert dritte["id"] == "6c"
    assert dritte["vorschlag"] is True


def test_die_kette_hebt_den_vorschlag_an_und_nennt_den_nachfolger(
    client: TestClient, owner, prozess_mit
) -> None:
    """A.4.2: wer einen kritischen Nachfolger speist, ist selbst kritisch."""
    kritisch = prozess_mit(name="Zahlungslauf", ausfallfolge="kritisch")
    speist = prozess_mit(
        name="Vorbereitung", ausfallfolge="gering", nachgelagert_ids=[kritisch["id"]]
    )
    bis = {"1a": False, "2a": False, "2b": False, "2c": False}
    bis |= {"3a": False, "3b": False, "3c": False}
    bis |= {"4a": False, "4b": False, "4c": False, "5a": False, "5b": False, "5c": False}

    frage = frage_im_wizard(client, owner, speist["id"], bis)
    assert frage["id"] == "6a"
    assert frage["vorschlag"] is True
    quellen = [b["quelle"] for b in frage["belege"]]
    assert quellen == ["prozess", "kette"]
    assert "Zahlungslauf" in frage["belege"][1]["text"]


# --- KI, IT und RG bleiben zu erklaeren -----------------------------------


@pytest.mark.parametrize("frage_id", ["1a", "4a", "5a"])
def test_ki_it_und_rg_bekommen_keinen_vorschlag(
    client: TestClient, owner, prozess_mit, datenobjekt, frage_id: str
) -> None:
    """A.8.4 nennt diese drei nicht als ableitbar — also wird geraten nichts."""
    entgelt = datenobjekt("Entgeltdaten", "besondere_kategorie")
    prozess = prozess_mit(input_datenobjekt_ids=[entgelt["id"]])
    bis: dict[str, bool] = {}
    if frage_id != "1a":
        bis = {"1a": False, "2a": True, "3a": True}
    if frage_id == "5a":
        bis |= {"4a": False, "4b": False, "4c": False}

    frage = frage_im_wizard(client, owner, prozess["id"], bis)
    assert frage["id"] == frage_id
    assert frage["vorschlag"] is None
    assert frage["belege"] == []


# --- Abweichung und Begruendung ------------------------------------------


def test_abweichung_ohne_begruendung_wird_nicht_angenommen(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    """Abnahme AP-4: der Schritt wird abgelehnt, nicht erst der Abschluss."""
    entgelt = datenobjekt("Entgeltdaten", "besondere_kategorie")
    prozess = prozess_mit(input_datenobjekt_ids=[entgelt["id"]])

    antwort = wizard(client, owner, prozess["id"], {"1a": False, "2a": False})
    assert antwort.status_code == 422
    assert "2a" in antwort.json()["detail"]


def test_abweichung_mit_begruendung_geht_durch_und_wird_festgehalten(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    entgelt = datenobjekt("Entgeltdaten", "besondere_kategorie")
    prozess = prozess_mit(input_datenobjekt_ids=[entgelt["id"]])
    antworten = antworten_fuer(profil_von(ds=2, mb=3, ur=2))

    antwort = abschliessen(
        client,
        owner,
        prozess["id"],
        antworten,
        begruendungen={
            "2a": "Das Objekt ist nur als Aggregat eingebunden, ohne Einzelwerte.",
            "6b": "Der Ausfall wird organisatorisch aufgefangen.",
        },
    )
    assert antwort.status_code == 201, antwort.text
    bewertung = antwort.json()["bewertung"]

    # Vorschlag und Antwort stehen beide da (Umsetzungsplan AP-4).
    assert bewertung["vorschlaege"]["2a"] is True
    assert bewertung["antworten"]["2a"] is False
    assert "Aggregat" in bewertung["abweichungen"]["2a"]


def test_begruendung_ohne_abweichung_wird_nicht_mitgeschleppt(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    """Ein Satz zu einer Frage, die am Ende zustimmt, dokumentiert nichts."""
    entgelt = datenobjekt("Entgeltdaten", "besondere_kategorie")
    prozess = prozess_mit(ausfallfolge="spuerbar", input_datenobjekt_ids=[entgelt["id"]])

    antwort = abschliessen(
        client,
        owner,
        prozess["id"],
        antworten_fuer(profil_von(ds=3, mb=3, ur=2)),
        begruendungen={"2a": "Steht hier ohne Not."},
    )
    assert antwort.status_code == 201, antwort.text
    assert antwort.json()["bewertung"]["abweichungen"] == {}


def test_leerer_begruendungstext_zaehlt_nicht(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    entgelt = datenobjekt("Entgeltdaten", "besondere_kategorie")
    prozess = prozess_mit(input_datenobjekt_ids=[entgelt["id"]])

    antwort = wizard(client, owner, prozess["id"], {"1a": False, "2a": False})
    assert antwort.status_code == 422
    mit_leerzeichen = client.post(
        f"/api/v1/prozesse/{prozess['id']}/bewertung/wizard",
        json={
            "antworten": {"1a": False, "2a": False},
            "begruendungen": {"2a": "   "},
        },
        headers=owner.kopf,
    )
    assert mit_leerzeichen.status_code == 422


# --- Ergebnisseite: Namen und Auflagen ------------------------------------


def test_ergebnis_nennt_die_klassen_mit_namen_und_erklaerung(
    client: TestClient, owner, prozess_mit
) -> None:
    """Abnahme AP-4: die Klassen stehen mit Namen da, nicht als Kuerzel."""
    prozess = prozess_mit(ausfallfolge="spuerbar")
    antwort = client.post(
        f"/api/v1/prozesse/{prozess['id']}/bewertung/wizard",
        json=nutzlast(profil_von(ds=3, mb=1, it=1, rg=2, ur=2)),
        headers=owner.kopf,
    )
    vorschau = antwort.json()["vorschau"]

    assert vorschau["tier"] == 3
    assert [k["kennung"] for k in vorschau["klassen"]] == [
        "K1",
        "K2",
        "K3",
        "K4",
        "K5",
        "K7",
        "K8",
        "K9",
    ]
    datenschutz = next(k for k in vorschau["klassen"] if k["kennung"] == "K4")
    assert datenschutz["name"] == "Datenschutz-Folgenabschätzung"
    assert "Art. 35" in datenschutz["erklaerung"]


def test_auflagen_gelten_kumulativ_bis_zum_erreichten_tier(
    client: TestClient, owner, prozess_mit
) -> None:
    """Abnahme AP-4: die Auflagen aus A.8.6 stehen am Ergebnis."""
    from app.services import bewertung as bewertung_service

    assert bewertung_service.auflagen(1) == list(bewertung_service.TIER_AUFLAGEN[1])
    assert bewertung_service.auflagen(3) == [
        *bewertung_service.TIER_AUFLAGEN[1],
        *bewertung_service.TIER_AUFLAGEN[2],
        *bewertung_service.TIER_AUFLAGEN[3],
    ]

    prozess = prozess_mit(ausfallfolge="gering")
    vorschau = client.post(
        f"/api/v1/prozesse/{prozess['id']}/bewertung/wizard",
        json=nutzlast(profil_von(ur=1)),
        headers=owner.kopf,
    ).json()["vorschau"]
    assert vorschau["tier"] == 1
    assert vorschau["auflagen"] == list(bewertung_service.TIER_AUFLAGEN[1])


# --- Cockpit: Antwort widerspricht Datenlage ------------------------------


def zeile(client: TestClient, anmeldung, schluessel: str) -> dict:
    antwort = client.get(f"/api/v1/cockpit/{schluessel}", headers=anmeldung.kopf)
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def test_begruendete_abweichung_ist_kein_cockpit_befund(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    """A.8.4 laesst die Abweichung zu — begruendet ist sie eine Entscheidung."""
    entgelt = datenobjekt("Entgeltdaten", "besondere_kategorie")
    prozess = prozess_mit(input_datenobjekt_ids=[entgelt["id"]])
    abschliessen(
        client,
        owner,
        prozess["id"],
        antworten_fuer(profil_von(ds=2, mb=3, ur=2)),
        begruendungen={
            "2a": "Nur als Aggregat eingebunden.",
            "6b": "Organisatorisch aufgefangen.",
        },
    )
    treffer = zeile(client, owner, "antwort_widerspricht_datenlage")
    assert [e for e in treffer["eintraege"] if e["id"] == prozess["id"]] == []


def test_geaenderte_datenlage_holt_die_alte_antwort_ins_cockpit(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    """Die Begruendung von damals bezieht sich auf eine Lage, die es nicht mehr gibt."""
    kontakt = datenobjekt("Personalstamm", "personenbezogen")
    prozess = prozess_mit(input_datenobjekt_ids=[kontakt["id"]])
    antwort = abschliessen(
        client,
        owner,
        prozess["id"],
        antworten_fuer(profil_von(ds=2, ur=2)),
        begruendungen={"6b": "Organisatorisch aufgefangen."},
    )
    assert antwort.status_code == 201, antwort.text
    assert zeile(client, owner, "antwort_widerspricht_datenlage")["eintraege"] == []

    # Jetzt wird umklassifiziert: 2a wuerde heute „ja" vorschlagen.
    umstufung = client.patch(
        f"/api/v1/datenobjekte/{kontakt['id']}",
        json={"kategorie": "besondere_kategorie"},
        headers=owner.kopf,
    )
    assert umstufung.status_code == 200, umstufung.text

    eintraege = zeile(client, owner, "antwort_widerspricht_datenlage")["eintraege"]
    hinweise = {
        e["hinweis"].split(":")[0]: e["hinweis"] for e in eintraege if e["id"] == prozess["id"]
    }
    # Die Umklassifizierung entwertet zwei Antworten auf einmal: den
    # Datenschutzblock und ueber die Konjunktion aus A.5 auch die Mitbestimmung.
    assert set(hinweise) == {"Frage 2a", "Frage 3a"}
    assert "damals nicht ableitbar, heute schon" in hinweise["Frage 2a"]
    assert "Personalstamm" in hinweise["Frage 2a"]
    assert eintraege[0]["ziel_modul"] == "prozesse"


def test_datenlage_geaendert_wird_von_unbegruendet_unterschieden(
    client: TestClient, owner, prozess_mit, datenobjekt
) -> None:
    """Beide Faelle sind Befunde — aber der Hinweis sagt, welcher es ist."""
    entgelt = datenobjekt("Entgeltdaten", "besondere_kategorie")
    prozess = prozess_mit(ausfallfolge="kritisch", input_datenobjekt_ids=[entgelt["id"]])
    abschliessen(
        client,
        owner,
        prozess["id"],
        antworten_fuer(profil_von(ds=2, mb=3, ur=3)),
        begruendungen={"2a": "Nur als Aggregat eingebunden."},
    )
    # Die Ausfallfolge sinkt: 6a schlaegt heute „nein" vor, geantwortet war „ja".
    gesenkt = client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"ausfallfolge": "gering"},
        headers=owner.kopf,
    )
    assert gesenkt.status_code == 200, gesenkt.text

    eintraege = zeile(client, owner, "antwort_widerspricht_datenlage")["eintraege"]
    hinweise = [e["hinweis"] for e in eintraege if e["id"] == prozess["id"]]
    assert len(hinweise) == 1
    assert "Frage 6a" in hinweise[0]
    assert "Datenlage seit der Bewertung geändert" in hinweise[0]


def test_ohne_bewertung_kein_befund(client: TestClient, owner, prozess_mit) -> None:
    prozess_mit(ausfallfolge="kritisch")
    assert zeile(client, owner, "antwort_widerspricht_datenlage")["eintraege"] == []
