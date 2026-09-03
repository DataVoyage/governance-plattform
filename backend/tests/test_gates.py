"""Selbstverpflichtung, Gates und Erinnerungen — Abnahmekriterien Phase 4."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.test_bewertung import nutzlast, profil_von

P_AUSSAGEN = ["PE1", "PE2", "PE3", "PE4", "PE5", "PE6"]
T_AUSSAGEN = ["TO1", "TO2", "TO3", "TO4", "TO5", "TO6"]


def alle_bestaetigt(ids: list[str]) -> dict:
    return {i: {"bestaetigt": True, "kommentar": ""} for i in ids}


@pytest.fixture
def owner(anmelden, rolle_geben, organisation):
    nutzer = anmelden("Prozess-Owner", subject="sub-owner")
    rolle_geben(nutzer.user_id, "prozess_owner", "organisationseinheit", organisation["fin_int"])
    return nutzer


@pytest.fixture
def vertretung(anmelden):
    return anmelden("Stellvertretung", subject="sub-vertretung")


@pytest.fixture
def governance(anmelden, rolle_geben):
    nutzer = anmelden("Governance", subject="sub-gov")
    rolle_geben(nutzer.user_id, "governance", "global")
    return nutzer


@pytest.fixture
def prozess(client: TestClient, owner, vertretung, prozess_daten):
    antwort = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    )
    assert antwort.status_code == 201, antwort.text
    return antwort.json()


def bewerte(client: TestClient, anmeldung, prozess_id: str, **profil):
    antwort = client.post(
        f"/api/v1/prozesse/{prozess_id}/bewertungen",
        json=nutzlast(profil_von(**profil)),
        headers=anmeldung.kopf,
    )
    assert antwort.status_code == 201, antwort.text
    return antwort.json()["bewertung"]


def gib_selbstverpflichtung(client: TestClient, anmeldung, prozess_id: str, aussagen=None):
    return client.post(
        "/api/v1/selbstverpflichtungen",
        json={
            "typ": "prozesseigner",
            "prozessobjekt_id": prozess_id,
            "aussagen": aussagen if aussagen is not None else alle_bestaetigt(P_AUSSAGEN),
        },
        headers=anmeldung.kopf,
    )


def gate_einreichen(client: TestClient, anmeldung, prozess_id: str, **daten):
    return client.post(f"/api/v1/prozesse/{prozess_id}/gates", json=daten, headers=anmeldung.kopf)


def gate_entscheiden(client: TestClient, anmeldung, gate_id: str, status: str, kommentar=""):
    return client.post(
        f"/api/v1/gates/{gate_id}/entscheidung",
        json={"status": status, "kommentar": kommentar},
        headers=anmeldung.kopf,
    )


# --- Katalog --------------------------------------------------------------


def test_katalog_liefert_die_nummerierten_aussagen(client: TestClient, owner) -> None:
    katalog = client.get("/api/v1/selbstverpflichtungen/katalog", headers=owner.kopf).json()
    je_typ = {eintrag["typ"]: eintrag["aussagen"] for eintrag in katalog}
    assert [a["id"] for a in je_typ["prozesseigner"]] == P_AUSSAGEN
    assert [a["id"] for a in je_typ["technischer_owner"]] == T_AUSSAGEN
    assert all(a["text"] for a in je_typ["prozesseigner"])


# --- Aktivierung ab Tier 3 (Abnahmekriterium 4.1) ------------------------


def test_tier_3_wird_ohne_selbstverpflichtung_nicht_aktiv(
    client: TestClient, owner, governance, prozess
) -> None:
    bewerte(client, owner, prozess["id"], ds=3)
    verweigert = client.patch(
        f"/api/v1/prozesse/{prozess['id']}", json={"status": "aktiv"}, headers=owner.kopf
    )
    assert verweigert.status_code == 422
    assert "Selbstverpflichtung" in verweigert.json()["detail"]

    gib_selbstverpflichtung(client, owner, prozess["id"])
    # Jetzt fehlt noch die Erstfreigabe durch Gate 1.
    ohne_gate = client.patch(
        f"/api/v1/prozesse/{prozess['id']}", json={"status": "aktiv"}, headers=owner.kopf
    )
    assert ohne_gate.status_code == 422
    assert "Gate 1" in ohne_gate.json()["detail"]

    gate = gate_einreichen(client, owner, prozess["id"], gate_typ="1").json()
    gate_entscheiden(client, governance, gate["id"], "freigegeben")

    aktiv = client.patch(
        f"/api/v1/prozesse/{prozess['id']}", json={"status": "aktiv"}, headers=owner.kopf
    )
    assert aktiv.status_code == 200, aktiv.text
    assert aktiv.json()["status"] == "aktiv"


def test_unvollstaendige_selbstverpflichtung_reicht_nicht(
    client: TestClient, owner, prozess
) -> None:
    bewerte(client, owner, prozess["id"], ds=3)
    teilweise = alle_bestaetigt(P_AUSSAGEN)
    teilweise["PE4"] = {"bestaetigt": False, "kommentar": "Noch offen"}
    abgegeben = gib_selbstverpflichtung(client, owner, prozess["id"], teilweise)
    assert abgegeben.status_code == 201
    assert abgegeben.json()["vollstaendig"] is False

    verweigert = client.patch(
        f"/api/v1/prozesse/{prozess['id']}", json={"status": "aktiv"}, headers=owner.kopf
    )
    assert verweigert.status_code == 422


def test_tier_1_und_2_brauchen_weder_selbstverpflichtung_noch_gate(
    client: TestClient, owner, prozess
) -> None:
    bewerte(client, owner, prozess["id"], ds=2)
    antwort = client.patch(
        f"/api/v1/prozesse/{prozess['id']}", json={"status": "aktiv"}, headers=owner.kopf
    )
    assert antwort.status_code == 200


def test_ohne_bewertung_kein_aktiver_prozess(client: TestClient, owner, prozess) -> None:
    antwort = client.patch(
        f"/api/v1/prozesse/{prozess['id']}", json={"status": "aktiv"}, headers=owner.kopf
    )
    assert antwort.status_code == 422
    assert "Bewertung" in antwort.json()["detail"]


def test_erneutes_setzen_auf_aktiv_prueft_nicht_erneut(client: TestClient, owner, prozess) -> None:
    bewerte(client, owner, prozess["id"], ds=1)
    client.patch(f"/api/v1/prozesse/{prozess['id']}", json={"status": "aktiv"}, headers=owner.kopf)
    nochmal = client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"status": "aktiv", "supplier": "Neu"},
        headers=owner.kopf,
    )
    assert nochmal.status_code == 200


# --- Selbstverpflichtung --------------------------------------------------


def test_selbstverpflichtung_ab_tier_3_ist_befristet(client: TestClient, owner, prozess) -> None:
    bewerte(client, owner, prozess["id"], ds=3)
    eintrag = gib_selbstverpflichtung(client, owner, prozess["id"]).json()
    assert eintrag["gueltig_bis"] is not None

    historie = client.get(
        f"/api/v1/prozesse/{prozess['id']}/selbstverpflichtungen", headers=owner.kopf
    ).json()
    assert len(historie) == 1


def test_selbstverpflichtung_unter_tier_3_ist_unbefristet(
    client: TestClient, owner, prozess
) -> None:
    bewerte(client, owner, prozess["id"], ds=1)
    eintrag = gib_selbstverpflichtung(client, owner, prozess["id"]).json()
    assert eintrag["gueltig_bis"] is None


def test_unbekannte_aussage_wird_abgelehnt(client: TestClient, owner, prozess) -> None:
    antwort = gib_selbstverpflichtung(
        client, owner, prozess["id"], {"P9": {"bestaetigt": True, "kommentar": ""}}
    )
    assert antwort.status_code == 422
    assert "P9" in antwort.json()["detail"]


def test_selbstverpflichtung_ohne_ziel(client: TestClient, owner) -> None:
    antwort = client.post(
        "/api/v1/selbstverpflichtungen",
        json={"typ": "prozesseigner", "aussagen": alle_bestaetigt(P_AUSSAGEN)},
        headers=owner.kopf,
    )
    assert antwort.status_code == 422

    ohne_tool = client.post(
        "/api/v1/selbstverpflichtungen",
        json={"typ": "technischer_owner", "aussagen": alle_bestaetigt(T_AUSSAGEN)},
        headers=owner.kopf,
    )
    assert ohne_tool.status_code == 422


def test_fremder_darf_keine_selbstverpflichtung_abgeben(
    client: TestClient, prozess, anmelden, governance
) -> None:
    fremder = anmelden("Ohne Rolle")
    assert gib_selbstverpflichtung(client, fremder, prozess["id"]).status_code == 403


def test_technischer_owner_verpflichtet_sich_fuer_sein_tool(
    client: TestClient, governance, organisation
) -> None:
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Landes-Tool", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    antwort = client.post(
        "/api/v1/selbstverpflichtungen",
        json={
            "typ": "technischer_owner",
            "tool_objekt_id": tool["id"],
            "aussagen": alle_bestaetigt(T_AUSSAGEN),
        },
        headers=governance.kopf,
    )
    assert antwort.status_code == 201
    assert antwort.json()["vollstaendig"] is True

    aktuell = client.get(
        f"/api/v1/tools/{tool['id']}/selbstverpflichtung", headers=governance.kopf
    ).json()
    assert aktuell["id"] == antwort.json()["id"]


def test_tool_selbstverpflichtung_erbt_die_befristung_des_prozesses(
    client: TestClient, governance, owner, prozess, attestieren
) -> None:
    bewerte(client, owner, prozess["id"], ds=3)
    tool = client.post(
        "/api/v1/tools", json={"name": "Tier-3-Tool"}, headers=governance.kopf
    ).json()
    attestieren(governance.kopf, tool["id"])
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    antwort = client.post(
        "/api/v1/selbstverpflichtungen",
        json={
            "typ": "technischer_owner",
            "tool_objekt_id": tool["id"],
            "aussagen": alle_bestaetigt(T_AUSSAGEN),
        },
        headers=governance.kopf,
    )
    assert antwort.json()["gueltig_bis"] is not None


# --- Gates (Abnahmekriterien 4.2, 4.3) -----------------------------------


def test_gate_2_ohne_ausloeser_wird_abgelehnt(client: TestClient, owner, prozess) -> None:
    """Abnahmekriterium 4.2."""
    antwort = gate_einreichen(client, owner, prozess["id"], gate_typ="2")
    assert antwort.status_code == 422
    assert "Auslöser" in antwort.json()["detail"]


def test_neues_externes_ziel_loest_gate_2_von_selbst_aus(
    client: TestClient, owner, governance, prozess
) -> None:
    """Leitdokument A.11 (Vorgang V-PRO-23).

    Wer ein Ziel ergaenzt, meldet damit den Ausloeser. Ihn zusaetzlich zum
    Einreichen aufzufordern hiesse, dem Anwender die Regel aufzubuerden, die
    die Anwendung selbst kennt.
    """
    bewerte(client, owner, prozess["id"], ur=1)
    client.patch(f"/api/v1/prozesse/{prozess['id']}", json={"status": "aktiv"}, headers=owner.kopf)

    antwort = client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"erlaubte_externe_ziele": ["sftp.partner.example"]},
        headers=owner.kopf,
    )
    assert antwort.status_code == 200
    assert antwort.json()["erlaubte_externe_ziele"] == ["sftp.partner.example"]

    gates = client.get(f"/api/v1/prozesse/{prozess['id']}/gates", headers=owner.kopf).json()
    assert [(g["gate_typ"], g["ausloeser"]) for g in gates] == [("2", "neues_externes_ziel")]
    assert "sftp.partner.example" in gates[0]["begruendung"]

    # Ein zweites Ziel verdoppelt den offenen Vorgang nicht.
    client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"erlaubte_externe_ziele": ["sftp.partner.example", "api.partner.example"]},
        headers=owner.kopf,
    )
    assert (
        len(client.get(f"/api/v1/prozesse/{prozess['id']}/gates", headers=owner.kopf).json()) == 1
    )
    del governance


def test_entwurf_loest_kein_gate_2_aus(client: TestClient, owner, prozess) -> None:
    """Ein Entwurf hat noch keinen Rahmen, den er verlassen koennte."""
    client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"erlaubte_externe_ziele": ["sftp.partner.example"]},
        headers=owner.kopf,
    )
    assert client.get(f"/api/v1/prozesse/{prozess['id']}/gates", headers=owner.kopf).json() == []


def test_unveraendertes_ziel_loest_kein_gate_2_aus(client: TestClient, owner, prozess) -> None:
    """Nur ein **neues** Ziel ist der Ausloeser, nicht jedes Speichern."""
    bewerte(client, owner, prozess["id"], ur=1)
    client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"status": "aktiv", "erlaubte_externe_ziele": ["sftp.partner.example"]},
        headers=owner.kopf,
    )
    vorher = client.get(f"/api/v1/prozesse/{prozess['id']}/gates", headers=owner.kopf).json()
    client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"erlaubte_externe_ziele": ["sftp.partner.example"], "output": "Andere Rechnung"},
        headers=owner.kopf,
    )
    nachher = client.get(f"/api/v1/prozesse/{prozess['id']}/gates", headers=owner.kopf).json()
    assert len(nachher) == len(vorher)


def test_gate_2_kennt_nur_die_fuenf_ausloeser(client: TestClient, owner, prozess) -> None:
    zulaessig = client.get("/api/v1/gates/ausloeser", headers=owner.kopf).json()
    assert len(zulaessig) == 5

    freier_grund = gate_einreichen(
        client, owner, prozess["id"], gate_typ="2", ausloeser="sonstiges"
    )
    assert freier_grund.status_code == 422

    gueltig = gate_einreichen(
        client,
        owner,
        prozess["id"],
        gate_typ="2",
        ausloeser=zulaessig[0],
        begruendung="Neue Datenkategorie erkannt",
    )
    assert gueltig.status_code == 201
    assert gueltig.json()["ausloeser"] == zulaessig[0]


def test_gate_1_kennt_keinen_ausloeser(client: TestClient, owner, prozess) -> None:
    antwort = gate_einreichen(
        client, owner, prozess["id"], gate_typ="1", ausloeser="neue_datenkategorie"
    )
    assert antwort.status_code == 422


def test_nur_governance_entscheidet(
    client: TestClient, owner, governance, prozess, anmelden
) -> None:
    """Abnahmekriterium 4.3."""
    gate = gate_einreichen(client, owner, prozess["id"], gate_typ="1").json()
    assert gate_entscheiden(client, owner, gate["id"], "freigegeben").status_code == 403

    auditor = anmelden("Auditor")
    assert gate_entscheiden(client, auditor, gate["id"], "freigegeben").status_code == 403

    entschieden = gate_entscheiden(client, governance, gate["id"], "freigegeben", "In Ordnung")
    assert entschieden.status_code == 200
    assert entschieden.json()["status"] == "freigegeben"
    assert entschieden.json()["entschieden_am"] is not None
    assert entschieden.json()["entscheidungskommentar"] == "In Ordnung"


def test_zwischenstatus_und_erneute_entscheidung(
    client: TestClient, owner, governance, prozess
) -> None:
    gate = gate_einreichen(client, owner, prozess["id"], gate_typ="1").json()
    in_pruefung = gate_entscheiden(client, governance, gate["id"], "in_pruefung")
    assert in_pruefung.status_code == 200
    assert in_pruefung.json()["entschieden_am"] is None

    abgelehnt = gate_entscheiden(client, governance, gate["id"], "abgelehnt", "Zu riskant")
    assert abgelehnt.status_code == 200

    nochmal = gate_entscheiden(client, governance, gate["id"], "freigegeben")
    assert nochmal.status_code == 422


def test_unzulaessiger_zielstatus(client: TestClient, owner, governance, prozess) -> None:
    gate = gate_einreichen(client, owner, prozess["id"], gate_typ="1").json()
    antwort = gate_entscheiden(client, governance, gate["id"], "eingereicht")
    assert antwort.status_code == 422


def test_kein_zweites_offenes_gate_desselben_typs(client: TestClient, owner, prozess) -> None:
    gate_einreichen(client, owner, prozess["id"], gate_typ="1")
    zweites = gate_einreichen(client, owner, prozess["id"], gate_typ="1")
    assert zweites.status_code == 422


def test_gate_historie_und_arbeitsvorrat(client: TestClient, owner, governance, prozess) -> None:
    erstes = gate_einreichen(client, owner, prozess["id"], gate_typ="1").json()
    gate_entscheiden(client, governance, erstes["id"], "abgelehnt", "Reichweite unklar")
    gate_einreichen(client, owner, prozess["id"], gate_typ="2", ausloeser="reichweitenerweiterung")

    historie = client.get(f"/api/v1/prozesse/{prozess['id']}/gates", headers=owner.kopf).json()
    assert len(historie) == 2

    offen = client.get("/api/v1/gates", headers=governance.kopf).json()
    assert [g["gate_typ"] for g in offen] == ["2"]


def test_fremder_sieht_keine_gates(client: TestClient, owner, prozess, anmelden) -> None:
    gate_einreichen(client, owner, prozess["id"], gate_typ="1")
    fremder = anmelden("Ohne Rolle")
    assert client.get("/api/v1/gates", headers=fremder.kopf).json() == []
    assert (
        client.get(f"/api/v1/prozesse/{prozess['id']}/gates", headers=fremder.kopf).status_code
        == 403
    )
    assert gate_einreichen(client, fremder, prozess["id"], gate_typ="1").status_code == 403


def test_unbekanntes_gate(client: TestClient, governance) -> None:
    antwort = gate_entscheiden(
        client, governance, "00000000-0000-0000-0000-000000000000", "freigegeben"
    )
    assert antwort.status_code == 404


# --- Erinnerungen (Abnahmekriterium 4.4) ---------------------------------


def test_erinnerung_60_tage_vor_ablauf_und_ueberfaelligkeit(
    client: TestClient, owner, prozess, db
) -> None:
    """Abnahmekriterium 4.4, geprueft als Datenzustand."""
    from app.models.governance import Benachrichtigung, Selbstverpflichtung
    from app.services import erinnerung

    bewerte(client, owner, prozess["id"], ds=3)
    eintrag_id = gib_selbstverpflichtung(client, owner, prozess["id"]).json()["id"]
    db.expire_all()
    eintrag = db.query(Selbstverpflichtung).one()
    frist = eintrag.gueltig_bis

    # Zu frueh: 61 Tage vor Ablauf passiert noch nichts.
    ergebnis = erinnerung.lauf(db, frist - timedelta(days=61))
    assert ergebnis.erinnert == []

    # 60 Tage vorher wird erinnert — und nur einmal.
    ergebnis = erinnerung.lauf(db, frist - timedelta(days=60))
    assert [str(i) for i in ergebnis.erinnert] == [eintrag_id]
    assert erinnerung.lauf(db, frist - timedelta(days=30)).erinnert == []

    nachricht = (
        db.query(Benachrichtigung)
        .filter(Benachrichtigung.anlass == erinnerung.ANLASS_ERINNERUNG)
        .one()
    )
    assert str(nachricht.empfaenger_user_id) == owner.user_id

    # Nach Fristablauf: ueberfaellig, ebenfalls nur einmal gemeldet.
    nach_ablauf = frist + timedelta(days=1)
    assert [str(i) for i in erinnerung.lauf(db, nach_ablauf).ueberfaellig] == [eintrag_id]
    assert erinnerung.lauf(db, nach_ablauf).ueberfaellig == []

    ueberfaellig = client.get(
        "/api/v1/selbstverpflichtungen/ueberfaellig", headers=owner.kopf
    ).json()
    assert ueberfaellig == []  # heute noch gueltig
    assert [str(e.id) for e in erinnerung.ueberfaellige_gesamt(db, nach_ablauf)] == [eintrag_id]


def test_ueberfaellige_zeigt_nur_den_eigenen_bereich(
    client: TestClient, owner, anmelden, prozess, db
) -> None:
    """Auch eine Auswertung ist eine Abfrage — sie darf nicht mehr zeigen als die Liste.

    Die Route ist der Vorgriff auf eine Cockpit-Zeile. Das Cockpit filtert seit
    jeher; diese Route tat es nicht und nannte jedem Angemeldeten, wer im
    ganzen Unternehmen eine Frist hat verstreichen lassen.
    """
    from app.models.governance import Selbstverpflichtung
    from app.services import erinnerung

    bewerte(client, owner, prozess["id"], ds=3)
    gib_selbstverpflichtung(client, owner, prozess["id"])
    db.expire_all()
    eintrag = db.query(Selbstverpflichtung).one()
    nach_ablauf = eintrag.gueltig_bis + timedelta(days=1)

    fremder = anmelden("Ohne Rolle")
    # Der Datenzustand kennt den Eintrag; die Antwort an den Fremden nicht.
    assert [str(e.id) for e in erinnerung.ueberfaellige_gesamt(db, nach_ablauf)] == [
        str(eintrag.id)
    ]
    assert (
        client.get("/api/v1/selbstverpflichtungen/ueberfaellig", headers=fremder.kopf).json() == []
    )


def test_abgelaufene_selbstverpflichtung_blockiert_die_aktivierung(
    client: TestClient, owner, governance, prozess, db
) -> None:
    from app.models.governance import Selbstverpflichtung
    from app.services import selbstverpflichtung as sv

    bewerte(client, owner, prozess["id"], ds=3)
    gib_selbstverpflichtung(client, owner, prozess["id"])
    gate = gate_einreichen(client, owner, prozess["id"], gate_typ="1").json()
    gate_entscheiden(client, governance, gate["id"], "freigegeben")

    db.expire_all()
    eintrag = db.query(Selbstverpflichtung).one()
    eintrag.gueltig_bis = datetime.now(UTC) - timedelta(days=1)
    db.commit()

    assert sv.ist_abgelaufen(eintrag) is True
    verweigert = client.patch(
        f"/api/v1/prozesse/{prozess['id']}", json={"status": "aktiv"}, headers=owner.kopf
    )
    assert verweigert.status_code == 422


def test_unbefristete_selbstverpflichtung_laeuft_nicht_ab(
    client: TestClient, owner, prozess, db
) -> None:
    from app.models.governance import Selbstverpflichtung
    from app.services import erinnerung
    from app.services import selbstverpflichtung as sv

    bewerte(client, owner, prozess["id"], ds=1)
    gib_selbstverpflichtung(client, owner, prozess["id"])
    db.expire_all()
    eintrag = db.query(Selbstverpflichtung).one()
    assert sv.ist_abgelaufen(eintrag) is False
    ergebnis = erinnerung.lauf(db, datetime.now(UTC) + timedelta(days=3650))
    assert ergebnis.erinnert == []
    assert ergebnis.ueberfaellig == []


def test_erinnerung_geht_an_den_technischen_owner(
    client: TestClient, governance, owner, prozess, db, attestieren
) -> None:
    from app.models.governance import Benachrichtigung, Selbstverpflichtung
    from app.services import erinnerung

    bewerte(client, owner, prozess["id"], ds=3)
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Tier-3-Tool", "technischer_owner_user_id": governance.user_id},
        headers=governance.kopf,
    ).json()
    attestieren(governance.kopf, tool["id"])
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    client.post(
        "/api/v1/selbstverpflichtungen",
        json={
            "typ": "technischer_owner",
            "tool_objekt_id": tool["id"],
            "aussagen": alle_bestaetigt(T_AUSSAGEN),
        },
        headers=governance.kopf,
    )
    db.expire_all()
    eintrag = db.query(Selbstverpflichtung).one()
    erinnerung.lauf(db, eintrag.gueltig_bis - timedelta(days=1))
    db.commit()
    nachricht = db.query(Benachrichtigung).one()
    assert str(nachricht.empfaenger_user_id) == governance.user_id

    eigene = client.get("/api/v1/benachrichtigungen", headers=governance.kopf).json()
    assert len(eigene) == 1
    assert eigene[0]["anlass"] == erinnerung.ANLASS_ERINNERUNG


def test_job_laesst_sich_starten(client: TestClient, owner, prozess, db) -> None:
    from app import jobs

    bewerte(client, owner, prozess["id"], ds=3)
    gib_selbstverpflichtung(client, owner, prozess["id"])
    db.commit()
    assert jobs.main(["erinnerungen"]) == 0
