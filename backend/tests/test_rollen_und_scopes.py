"""Die Matrix aus ``docs/rollen-und-scopes.md`` als ausfuehrbare Tabelle.

Rollen und Rechte sind nichts Zufaelliges — an ihnen haengt, ob die Anwendung
benutzbar ist und ob man ihr glauben kann. Deshalb wird hier **jede Zelle**
gepruft, nicht nur die interessanten: fuer jede Handlung laeuft jeder der elf
Zugaenge, und die Erwartung sagt fuer jeden einzelnen, ob er darf oder nicht.
Eine Handlung ohne vollstaendige Erwartung gibt es nicht; wer eine Rolle
vergisst, faellt beim Aufbau der Tabelle durch (siehe ``test_matrix_ist_vollstaendig``).

Damit ist der negative Fall genauso belegt wie der positive: ``pytest -k
rollen_und_scopes`` faehrt jede Kombination einmal an. Ein neues Recht, das
nirgends verweigert wird, faellt hier auf.

**Der Aufbau.** Zwei Fachbereiche, damit es immer ein Gegenueber gibt:

* *Vertrieb* mit INT, DE und FR — hier liegen die Objekte, um die es geht:
  ein Prozessobjekt (Prozessgeber INT, Umsetzung in DE), ein Tool-Objekt an
  der Einheit DE, mit dem Prozess verknuepft, und ein Datenobjekt des
  Fachbereichs, das der Prozess als Input nutzt und das Tool liest.
* *Personal* mit INT und je einem eigenen Prozess-, Tool- und Datenobjekt.
  Sie sind die Gegenprobe: kein Zugang aus dem Vertrieb darf sie sehen.

Jeder Zugang traegt genau eine Rolle in genau einem Bereich. Das ist der
Punkt: eine Berechtigung entsteht aus Rolle **mal** Bereich (P-App-3), und
beide Haelften werden hier einzeln widerlegt — dieselbe Rolle im falschen
Bereich, und der falsche Bereich mit der richtigen Rolle.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

# --- Die elf Zugaenge -------------------------------------------------------
#
# Acht Rollen aus A.15, dazu zwei Faelle, an denen sich die Regel zeigt:
# dieselbe Rolle mit engerem Bereich, und ein Zugang ganz ohne Rolle.

GOVERNANCE = "governance"
PLATTFORM = "plattform"
AUDITOR = "auditor"
ADMINISTRATOR = "administrator"
#: Prozess-Owner fuer den ganzen Fachbereich Vertrieb.
OWNER_FB = "prozess_owner_fachbereich"
#: Dieselbe Rolle, aber nur fuer die Einheit INT.
OWNER_INT = "prozess_owner_einheit"
#: Prozess-Umsetzer in Vertrieb DE — dort wird der Prozess umgesetzt.
UMSETZER = "prozess_umsetzer"
TECHNIKER = "technischer_owner"
DATENOWNER = "datenobjekt_owner"
#: Prozess-Owner im *anderen* Fachbereich: die Rolle stimmt, der Bereich nicht.
FREMDER = "fremder_prozess_owner"
OHNE_ROLLE = "ohne_rolle"

ZUGAENGE: tuple[str, ...] = (
    GOVERNANCE,
    PLATTFORM,
    AUDITOR,
    ADMINISTRATOR,
    OWNER_FB,
    OWNER_INT,
    UMSETZER,
    TECHNIKER,
    DATENOWNER,
    FREMDER,
    OHNE_ROLLE,
)

#: Wer bereichsuebergreifend liest (A.15, Architektur 4.3). Der
#: App-Administrator gehoert ausdruecklich nicht dazu: er vergibt jeden
#: Zugriff und bekommt deshalb selbst keinen fachlichen.
GLOBAL_LESEND = frozenset({GOVERNANCE, PLATTFORM, AUDITOR})

#: Wer das Prozessobjekt des Vertriebs sehen darf. Der technische Owner ueber
#: sein Tool (er muss die Einstufung nachvollziehen koennen, A.4.4), der
#: Umsetzer ueber seine Umsetzung.
SIEHT_PROZESS = GLOBAL_LESEND | {OWNER_FB, OWNER_INT, UMSETZER, TECHNIKER}

#: Wer das Tool-Objekt sehen darf — ueber die Einheit oder ueber die
#: Prozesskante.
SIEHT_TOOL = GLOBAL_LESEND | {OWNER_FB, OWNER_INT, UMSETZER, TECHNIKER}

#: Wer das Datenobjekt sehen darf: sein Fachbereich, und jeder, der es ueber
#: einen sichtbaren Prozess oder ein sichtbares Tool beruehrt.
SIEHT_DATENOBJEKT = SIEHT_PROZESS | {DATENOWNER}

#: Wer das Prozessobjekt schreibt: der Prozess-Owner am Prozessgeber.
SCHREIBT_PROZESS = frozenset({GOVERNANCE, OWNER_FB, OWNER_INT})

#: Wer das Tool-Objekt schreibt: sein technischer Owner. Der Prozess-Owner
#: gehoert nicht dazu — das Tool gehoert ihm nicht (A.10.3).
SCHREIBT_TOOL = frozenset({GOVERNANCE, TECHNIKER})


@dataclass
class Welt:
    """Der Aufbau: zwei Fachbereiche, je ein Satz Objekte, elf Zugaenge."""

    client: TestClient
    zugaenge: dict[str, object]
    fachbereich: str
    fremder_fachbereich: str
    int_id: str
    de_id: str
    fremde_int_id: str
    prozess: str
    umsetzung: str
    tool: str
    datenobjekt: str
    fremder_prozess: str
    fremdes_tool: str
    fremdes_datenobjekt: str
    zweites_datenobjekt: str
    #: Ohne Kategorie — damit die Cockpit-Zeile etwas zu zeigen hat.
    unkategorisiert: str
    #: Vorgefunden und unbestaetigt: der eine Schreibweg der Plattform.
    importiertes_tool: str
    importiertes_datenobjekt: str
    gate: str

    def kopf(self, zugang: str) -> dict[str, str]:
        return self.zugaenge[zugang].kopf  # type: ignore[union-attr]


@dataclass(frozen=True)
class Handlung:
    """Eine Handlung und die vollstaendige Liste derer, die sie ausfuehren duerfen."""

    name: str
    #: Fuehrt die Handlung aus und liefert einen HTTP-Status. Fuer Listen gilt:
    #: 200, wenn das gesuchte Objekt enthalten ist, sonst 403 — eine Liste, die
    #: das Objekt verschweigt, verweigert es (E-54).
    ausfuehren: Callable[[Welt, str], int]
    erlaubt: frozenset[str] = field(default_factory=frozenset)


def _in_liste(welt: Welt, zugang: str, pfad: str, gesucht: str) -> int:
    antwort = welt.client.get(pfad, headers=welt.kopf(zugang))
    if antwort.status_code >= 400:
        return antwort.status_code
    return 200 if any(e["id"] == gesucht for e in antwort.json()) else 403


def _in_zeile(welt: Welt, zugang: str, pfad: str, gesucht: str) -> int:
    """Wie ``_in_liste``, aber fuer eine Cockpit-Zeile mit ``eintraege``."""
    antwort = welt.client.get(pfad, headers=welt.kopf(zugang))
    if antwort.status_code >= 400:
        return antwort.status_code
    return 200 if any(e["id"] == gesucht for e in antwort.json()["eintraege"]) else 403


def _status(antwort) -> int:
    return antwort.status_code


#: Eine vollstaendige Wizard-Nutzlast. Ein synthetisch gesetztes Zielprofil
#: widerspricht der Datenlage fast immer, deshalb liegt zu jeder Frage eine
#: Begruendung bei — der Server behaelt nur die, wo es wirklich abweicht.
_ANTWORTEN = {f"{block}{frage}": False for block in range(1, 7) for frage in ("a", "b", "c")}
_BEWERTUNG = {
    "antworten": _ANTWORTEN,
    "begruendungen": dict.fromkeys(_ANTWORTEN, "Fuer diese Pruefung bewusst gesetzt."),
}


# --- Der Aufbau -------------------------------------------------------------


@pytest.fixture
def welt(client: TestClient, anmelden, rolle_geben, db) -> Welt:
    from app.models.enums import Ebene
    from app.models.organisation import Fachbereich, Organisationseinheit

    vertrieb = Fachbereich(name="Vertrieb", code="fb-vertrieb")
    personal = Fachbereich(name="Personal", code="fb-personal")
    db.add_all([vertrieb, personal])
    db.flush()
    v_int = Organisationseinheit(fachbereich_id=vertrieb.id, ebene=Ebene.INT)
    v_de = Organisationseinheit(fachbereich_id=vertrieb.id, ebene=Ebene.LAND, land_code="DE")
    v_fr = Organisationseinheit(fachbereich_id=vertrieb.id, ebene=Ebene.LAND, land_code="FR")
    p_int = Organisationseinheit(fachbereich_id=personal.id, ebene=Ebene.INT)
    db.add_all([v_int, v_de, v_fr, p_int])
    db.commit()
    fb, fremd_fb = str(vertrieb.id), str(personal.id)
    int_id, de_id, fremde_int = str(v_int.id), str(v_de.id), str(p_int.id)

    zugaenge: dict[str, object] = {}
    rollen = {
        GOVERNANCE: ("governance", "global", None),
        PLATTFORM: ("plattform", "global", None),
        AUDITOR: ("auditor", "global", None),
        ADMINISTRATOR: ("app_administrator", "global", None),
        OWNER_FB: ("prozess_owner", "fachbereich", fb),
        OWNER_INT: ("prozess_owner", "organisationseinheit", int_id),
        UMSETZER: ("prozess_umsetzer", "organisationseinheit", de_id),
        TECHNIKER: ("technischer_owner", "fachbereich", fb),
        DATENOWNER: ("datenobjekt_owner", "fachbereich", fb),
        FREMDER: ("prozess_owner", "fachbereich", fremd_fb),
    }
    for kennung, (rolle, scope_typ, scope_id) in rollen.items():
        nutzer = anmelden(kennung, subject=f"sub-{kennung}")
        rolle_geben(nutzer.user_id, rolle, scope_typ, scope_id)
        zugaenge[kennung] = nutzer
    zugaenge[OHNE_ROLLE] = anmelden(OHNE_ROLLE, subject="sub-ohne-rolle")

    gov = zugaenge[GOVERNANCE].kopf  # type: ignore[union-attr]
    # Ein Dritter als Eigner: sonst faellt jede Regel mit der persoenlichen
    # Verantwortung zusammen und die Bereichsregel waere nicht gepruft.
    eigner = anmelden("Eigner", subject="sub-eigner")

    def datenobjekt(name: str, fachbereich_id: str) -> str:
        antwort = client.post(
            "/api/v1/datenobjekte",
            json={"name": name, "fachbereich_id": fachbereich_id, "kategorie": "intern"},
            headers=gov,
        )
        assert antwort.status_code == 201, antwort.text
        return antwort.json()["id"]

    def prozess(name: str, geber: str, umsetzung_ids: list[str], daten: list[str]) -> dict:
        antwort = client.post(
            "/api/v1/prozesse",
            json={
                "name": name,
                "owner_user_id": eigner.user_id,
                "stellvertretung_user_id": eigner.user_id,
                "prozessgeber_org_id": geber,
                "supplier": "Vorsystem",
                "process_steps": "Pruefen; freigeben; buchen",
                "output": "Ergebnis",
                "customer": "bereich",
                "ausfallfolge": "spuerbar",
                "input_datenobjekt_ids": daten,
                "umsetzung_land_org_ids": umsetzung_ids,
            },
            headers=gov,
        )
        assert antwort.status_code == 201, antwort.text
        return antwort.json()

    def tool(name: str, einheit: str, prozess_id: str, datenobjekt_id: str) -> str:
        angelegt = client.post(
            "/api/v1/tools",
            json={"name": name, "organisationseinheit_id": einheit},
            headers=gov,
        )
        assert angelegt.status_code == 201, angelegt.text
        tool_id = angelegt.json()["id"]
        client.put(
            f"/api/v1/tools/{tool_id}/attestierungen",
            json={
                "attest_entscheidung_ueber_personen": False,
                "attest_mensch_dazwischen": True,
                "attest_undeklarierte_quellen": False,
            },
            headers=gov,
        )
        verknuepft = client.post(
            f"/api/v1/tools/{tool_id}/prozesse",
            json={"prozessobjekt_id": prozess_id},
            headers=gov,
        )
        assert verknuepft.status_code in (200, 201), verknuepft.text
        client.post(
            f"/api/v1/tools/{tool_id}/datenobjekte",
            json={"datenobjekt_id": datenobjekt_id, "zugriffsart": "lesen"},
            headers=gov,
        )
        return tool_id

    do = datenobjekt("Filialstammdaten", fb)
    p = prozess("Bestellvorschlag", int_id, [de_id], [do])
    t = tool("Bestellskript", de_id, p["id"], do)

    fremd_do = datenobjekt("Personalstammdaten", fremd_fb)
    fremd_p = prozess("Entgeltabrechnung", fremde_int, [], [fremd_do])
    fremd_t = tool("Abrechnungsskript", fremde_int, fremd_p["id"], fremd_do)

    zweites_do = datenobjekt("Aktionsplanung", fb)
    ohne_kategorie = client.post(
        "/api/v1/datenobjekte",
        json={"name": "Kassenjournal", "fachbereich_id": fb},
        headers=gov,
    )
    assert ohne_kategorie.status_code == 201, ohne_kategorie.text

    # Zwei vorgefundene Objekte. Sie sind der einzige Fall, in dem die
    # Plattform schreibt — und der einzige, in dem ein Objekt zunaechst
    # niemandem gehoert (A.16).
    plattform_kopf = zugaenge[PLATTFORM].kopf  # type: ignore[union-attr]
    client.post(
        "/api/v1/import/assets",
        json={
            "quelle": "zentrale-entwicklungsplattform",
            "datensaetze": [
                {"typ": "tool", "externe_id": "T-1", "name": "Vorgefundenes Skript"},
                {"typ": "datenobjekt", "externe_id": "D-1", "name": "Vorgefundene Ablage"},
            ],
        },
        headers=plattform_kopf,
    )
    imp_tool = next(
        e["id"]
        for e in client.get("/api/v1/tools", headers=gov).json()
        if e["name"] == "Vorgefundenes Skript"
    )
    imp_do = next(
        e["id"]
        for e in client.get("/api/v1/datenobjekte", headers=gov).json()
        if e["name"] == "Vorgefundene Ablage"
    )
    # Bestaetigen heisst zuordnen: erst der Anker, dann der Status (7.2).
    client.patch(
        f"/api/v1/datenobjekte/{imp_do}",
        json={"fachbereich_id": fb},
        headers=plattform_kopf,
    )
    client.patch(
        f"/api/v1/tools/{imp_tool}",
        json={"organisationseinheit_id": de_id},
        headers=gov,
    )

    # Der offene Gate-Vorgang haengt an einem zweiten Prozess: „einreichen"
    # scheitert sonst daran, dass fuer denselben Prozess schon einer offen ist.
    p_gate = prozess("Aktionssteuerung", int_id, [], [])
    eingereicht = client.post(
        f"/api/v1/prozesse/{p_gate['id']}/gates",
        json={"gate_typ": "2", "ausloeser": "neue_datenkategorie", "begruendung": "Aufbau"},
        headers=gov,
    )
    assert eingereicht.status_code == 201, eingereicht.text

    return Welt(
        client=client,
        zugaenge=zugaenge,
        fachbereich=fb,
        fremder_fachbereich=fremd_fb,
        int_id=int_id,
        de_id=de_id,
        fremde_int_id=fremde_int,
        prozess=p["id"],
        umsetzung=p["umsetzungen"][0]["id"],
        tool=t,
        datenobjekt=do,
        fremder_prozess=fremd_p["id"],
        fremdes_tool=fremd_t,
        fremdes_datenobjekt=fremd_do,
        zweites_datenobjekt=zweites_do,
        unkategorisiert=ohne_kategorie.json()["id"],
        importiertes_tool=imp_tool,
        importiertes_datenobjekt=imp_do,
        gate=eingereicht.json()["id"],
    )


# --- Die Matrix -------------------------------------------------------------


def _prozess_nutzlast(welt: Welt, zugang: str) -> dict:
    eigner = welt.zugaenge[zugang]
    return {
        "name": "Neu angelegt",
        "owner_user_id": eigner.user_id,  # type: ignore[union-attr]
        "stellvertretung_user_id": eigner.user_id,  # type: ignore[union-attr]
        "prozessgeber_org_id": welt.int_id,
        "supplier": "Vorsystem",
        "process_steps": "Ein Schritt",
        "output": "Ergebnis",
        "customer": "bereich",
        "ausfallfolge": "spuerbar",
    }


HANDLUNGEN: tuple[Handlung, ...] = (
    # --- Prozessobjekt: sehen -----------------------------------------------
    Handlung(
        "prozess_liste",
        lambda w, z: _in_liste(w, z, "/api/v1/prozesse", w.prozess),
        SIEHT_PROZESS,
    ),
    Handlung(
        "prozess_detail",
        lambda w, z: _status(w.client.get(f"/api/v1/prozesse/{w.prozess}", headers=w.kopf(z))),
        SIEHT_PROZESS,
    ),
    Handlung(
        "fremdes_prozessobjekt",
        lambda w, z: _status(
            w.client.get(f"/api/v1/prozesse/{w.fremder_prozess}", headers=w.kopf(z))
        ),
        GLOBAL_LESEND | {FREMDER},
    ),
    # --- Prozessobjekt: schreiben -------------------------------------------
    Handlung(
        "prozess_anlegen",
        lambda w, z: _status(
            w.client.post("/api/v1/prozesse", json=_prozess_nutzlast(w, z), headers=w.kopf(z))
        ),
        SCHREIBT_PROZESS,
    ),
    Handlung(
        "prozess_aendern",
        lambda w, z: _status(
            w.client.patch(
                f"/api/v1/prozesse/{w.prozess}",
                json={"supplier": "Geaendert"},
                headers=w.kopf(z),
            )
        ),
        SCHREIBT_PROZESS,
    ),
    Handlung(
        "prozess_bewerten",
        lambda w, z: _status(
            w.client.post(
                f"/api/v1/prozesse/{w.prozess}/bewertungen",
                json=_BEWERTUNG,
                headers=w.kopf(z),
            )
        ),
        SCHREIBT_PROZESS,
    ),
    Handlung(
        "selbstverpflichtung_prozesseigner",
        lambda w, z: _status(
            w.client.post(
                "/api/v1/selbstverpflichtungen",
                json={"typ": "prozesseigner", "prozessobjekt_id": w.prozess, "aussagen": {}},
                headers=w.kopf(z),
            )
        ),
        SCHREIBT_PROZESS,
    ),
    Handlung(
        "gate_einreichen",
        lambda w, z: _status(
            w.client.post(
                f"/api/v1/prozesse/{w.prozess}/gates",
                json={"gate_typ": "2", "ausloeser": "neue_datenkategorie", "begruendung": "x"},
                headers=w.kopf(z),
            )
        ),
        SCHREIBT_PROZESS,
    ),
    Handlung(
        "gate_entscheiden",
        lambda w, z: _status(
            w.client.post(
                f"/api/v1/gates/{w.gate}/entscheidung",
                json={"status": "freigegeben", "kommentar": "geprüft"},
                headers=w.kopf(z),
            )
        ),
        frozenset({GOVERNANCE}),
    ),
    Handlung(
        "umsetzung_pflegen",
        lambda w, z: _status(
            w.client.patch(
                f"/api/v1/prozesse/{w.prozess}/umsetzungen/{w.umsetzung}",
                json={"lokale_abweichung": "Lokale Freigabe"},
                headers=w.kopf(z),
            )
        ),
        SCHREIBT_PROZESS | {UMSETZER},
    ),
    # --- Tool-Objekt: sehen --------------------------------------------------
    Handlung(
        "tool_liste",
        lambda w, z: _in_liste(w, z, "/api/v1/tools", w.tool),
        SIEHT_TOOL,
    ),
    Handlung(
        "tool_detail",
        lambda w, z: _status(w.client.get(f"/api/v1/tools/{w.tool}", headers=w.kopf(z))),
        SIEHT_TOOL,
    ),
    Handlung(
        "fremdes_tool",
        lambda w, z: _status(w.client.get(f"/api/v1/tools/{w.fremdes_tool}", headers=w.kopf(z))),
        GLOBAL_LESEND | {FREMDER},
    ),
    # --- Tool-Objekt: schreiben ---------------------------------------------
    Handlung(
        "tool_anlegen",
        lambda w, z: _status(
            w.client.post(
                "/api/v1/tools",
                json={"name": "Neues Tool", "organisationseinheit_id": w.de_id},
                headers=w.kopf(z),
            )
        ),
        SCHREIBT_TOOL,
    ),
    Handlung(
        "tool_aendern",
        lambda w, z: _status(
            w.client.patch(
                f"/api/v1/tools/{w.tool}",
                json={"beschreibung": "Geaendert"},
                headers=w.kopf(z),
            )
        ),
        SCHREIBT_TOOL,
    ),
    Handlung(
        "tool_attestieren",
        lambda w, z: _status(
            w.client.put(
                f"/api/v1/tools/{w.tool}/attestierungen",
                json={
                    "attest_entscheidung_ueber_personen": False,
                    "attest_mensch_dazwischen": True,
                    "attest_undeklarierte_quellen": False,
                },
                headers=w.kopf(z),
            )
        ),
        SCHREIBT_TOOL,
    ),
    Handlung(
        "tool_zustand_melden",
        lambda w, z: _status(
            w.client.post(
                f"/api/v1/tools/{w.tool}/compliance",
                json={"farbe": "gruen", "begruendung": "geprüft"},
                headers=w.kopf(z),
            )
        ),
        SCHREIBT_TOOL,
    ),
    Handlung(
        "selbstverpflichtung_technischer_owner",
        lambda w, z: _status(
            w.client.post(
                "/api/v1/selbstverpflichtungen",
                json={"typ": "technischer_owner", "tool_objekt_id": w.tool, "aussagen": {}},
                headers=w.kopf(z),
            )
        ),
        SCHREIBT_TOOL,
    ),
    Handlung(
        # Die Kante hat zwei Enden: wer eines traegt, darf sie knuepfen (A.4.4).
        "tool_datenkante_setzen",
        lambda w, z: _status(
            w.client.post(
                f"/api/v1/tools/{w.tool}/datenobjekte",
                json={"datenobjekt_id": w.zweites_datenobjekt, "zugriffsart": "lesen"},
                headers=w.kopf(z),
            )
        ),
        SCHREIBT_TOOL | {OWNER_FB, OWNER_INT},
    ),
    # --- Datenobjekt ---------------------------------------------------------
    Handlung(
        "datenobjekt_liste",
        lambda w, z: _in_liste(w, z, "/api/v1/datenobjekte", w.datenobjekt),
        SIEHT_DATENOBJEKT,
    ),
    Handlung(
        "datenobjekt_detail",
        lambda w, z: _status(
            w.client.get(f"/api/v1/datenobjekte/{w.datenobjekt}", headers=w.kopf(z))
        ),
        SIEHT_DATENOBJEKT,
    ),
    Handlung(
        "fremdes_datenobjekt",
        lambda w, z: _status(
            w.client.get(f"/api/v1/datenobjekte/{w.fremdes_datenobjekt}", headers=w.kopf(z))
        ),
        GLOBAL_LESEND | {FREMDER},
    ),
    Handlung(
        # Der Katalog ist die eine, schmale Ausnahme: vier Felder jeder
        # bestaetigten Quelle, damit ein fremder Prozess sie als Input nennen
        # kann (A.7). Ohne Rolle gibt es auch ihn nicht.
        "datenobjekt_katalog",
        lambda w, z: _in_liste(w, z, "/api/v1/datenobjekte/katalog", w.fremdes_datenobjekt),
        frozenset(ZUGAENGE) - {OHNE_ROLLE},
    ),
    Handlung(
        "datenobjekt_anlegen",
        lambda w, z: _status(
            w.client.post(
                "/api/v1/datenobjekte",
                json={"name": "Neue Quelle", "fachbereich_id": w.fachbereich},
                headers=w.kopf(z),
            )
        ),
        frozenset({GOVERNANCE, DATENOWNER}),
    ),
    Handlung(
        "datenobjekt_stammdaten",
        lambda w, z: _status(
            w.client.patch(
                f"/api/v1/datenobjekte/{w.datenobjekt}",
                json={"quellsystem": "SAP"},
                headers=w.kopf(z),
            )
        ),
        frozenset({GOVERNANCE, DATENOWNER}),
    ),
    Handlung(
        "datenobjekt_kategorie",
        lambda w, z: _status(
            w.client.patch(
                f"/api/v1/datenobjekte/{w.datenobjekt}",
                json={"kategorie": "vertraulich"},
                headers=w.kopf(z),
            )
        ),
        frozenset({GOVERNANCE, DATENOWNER}),
    ),
    Handlung(
        "datenobjekt_anker_wechseln",
        lambda w, z: _status(
            w.client.patch(
                f"/api/v1/datenobjekte/{w.datenobjekt}",
                json={"fachbereich_id": w.fremder_fachbereich},
                headers=w.kopf(z),
            )
        ),
        frozenset({GOVERNANCE}),
    ),
    Handlung(
        # Der zweite Weg zu einem Datenobjekt: als Output des eigenen Prozesses.
        # Der Fachbereich wird nicht gewaehlt, er ergibt sich (7.2).
        "datenobjekt_anlegen_als_output",
        lambda w, z: _status(
            w.client.post(
                "/api/v1/datenobjekte",
                json={"name": "Erzeugte Quelle", "prozessobjekt_id": w.prozess},
                headers=w.kopf(z),
            )
        ),
        SCHREIBT_PROZESS,
    ),
    # --- Die Nutzlast erteilt keine Erlaubnis --------------------------------
    #
    # Die Handlungen oben schicken das, was ein Formular schicken wuerde. Diese
    # hier schicken, was jemand schicken *koennte*: sich selbst als Owner. Bis
    # AP-13 genuegte das, um ein Tool-Objekt anzulegen — jeder Angemeldete
    # erfuellte damit die Bedingung, die er gerade erst gesetzt hatte (E-58).
    Handlung(
        "tool_anlegen_mit_sich_selbst_als_owner",
        lambda w, z: _status(
            w.client.post(
                "/api/v1/tools",
                json={
                    "name": "Selbst erklaert",
                    "organisationseinheit_id": w.de_id,
                    "technischer_owner_user_id": w.zugaenge[z].user_id,  # type: ignore[union-attr]
                },
                headers=w.kopf(z),
            )
        ),
        SCHREIBT_TOOL,
    ),
    Handlung(
        "prozess_anlegen_im_fremden_bereich",
        lambda w, z: _status(
            w.client.post(
                "/api/v1/prozesse",
                json={**_prozess_nutzlast(w, z), "prozessgeber_org_id": w.fremde_int_id},
                headers=w.kopf(z),
            )
        ),
        frozenset({GOVERNANCE, FREMDER}),
    ),
    # --- Vorgefundene Objekte: der eine Schreibweg der Plattform -------------
    Handlung(
        "importiertes_tool_bestaetigen",
        lambda w, z: _status(
            w.client.post(f"/api/v1/tools/{w.importiertes_tool}/bestaetigung", headers=w.kopf(z))
        ),
        frozenset({GOVERNANCE, PLATTFORM, TECHNIKER}),
    ),
    Handlung(
        "importiertes_datenobjekt_bestaetigen",
        lambda w, z: _status(
            w.client.post(
                f"/api/v1/datenobjekte/{w.importiertes_datenobjekt}/bestaetigung",
                headers=w.kopf(z),
            )
        ),
        frozenset({GOVERNANCE, PLATTFORM, DATENOWNER}),
    ),
    Handlung(
        # Die Plattform betreibt die Adapter — das ist ihr einziger Schreibweg
        # neben der Bestaetigung, und niemand sonst hat ihn. Auch die
        # Governance nicht: ein Import ist keine fachliche Entscheidung,
        # sondern ein Betriebsvorgang mit einer Identitaet.
        "assets_importieren",
        lambda w, z: _status(
            w.client.post(
                "/api/v1/import/assets",
                json={
                    "quelle": "zentrale-entwicklungsplattform",
                    "datensaetze": [
                        {"typ": "tool", "externe_id": "T-neu", "name": "Weiteres Skript"}
                    ],
                },
                headers=w.kopf(z),
            )
        ),
        frozenset({PLATTFORM}),
    ),
    # --- Regelwerk, Auswertung, Verwaltung -----------------------------------
    Handlung(
        # Das Regelwerk liest jeder: wer bewertet wird, muss den Massstab kennen.
        "technologiematrix_lesen",
        lambda w, z: _status(w.client.get("/api/v1/technologiematrix", headers=w.kopf(z))),
        frozenset(ZUGAENGE),
    ),
    Handlung(
        "technologiematrix_schreiben",
        lambda w, z: _status(
            w.client.put(
                "/api/v1/technologiematrix/apps-script/K1",
                json={"bewertung": "erfuellt", "begruendung": "geprüft"},
                headers=w.kopf(z),
            )
        ),
        frozenset({GOVERNANCE}),
    ),
    Handlung(
        "einstellung_schreiben",
        lambda w, z: _status(
            w.client.put(
                "/api/v1/konfiguration/asset_inaktiv_tage",
                json={"wert": "180"},
                headers=w.kopf(z),
            )
        ),
        frozenset({GOVERNANCE}),
    ),
    Handlung(
        "nachweis_lesen",
        lambda w, z: _status(w.client.get("/api/v1/nachweis", headers=w.kopf(z))),
        GLOBAL_LESEND | {ADMINISTRATOR},
    ),
    Handlung(
        "nutzerverwaltung",
        lambda w, z: _status(w.client.get("/api/v1/admin/users", headers=w.kopf(z))),
        GLOBAL_LESEND | {ADMINISTRATOR},
    ),
    Handlung(
        "rolle_vergeben",
        lambda w, z: _status(
            w.client.post(
                "/api/v1/admin/rollenzuweisungen",
                json={
                    "user_id": w.zugaenge[OHNE_ROLLE].user_id,  # type: ignore[union-attr]
                    "rolle": "prozess_owner",
                    "scope_typ": "organisationseinheit",
                    "scope_id": w.int_id,
                },
                headers=w.kopf(z),
            )
        ),
        frozenset({ADMINISTRATOR}),
    ),
    Handlung(
        # Auswahllisten sind Teil der Berechtigung (E-56): wer die Rolle im
        # Bereich nicht traegt, bekommt dort auch keine Personen genannt.
        "personen_im_bereich",
        lambda w, z: _status(
            w.client.get(
                f"/api/v1/personen?rolle=prozess_owner&organisationseinheit_id={w.int_id}",
                headers=w.kopf(z),
            )
        ),
        frozenset({GOVERNANCE, OWNER_FB, OWNER_INT}),
    ),
    Handlung(
        "bereichsauswahl_prozessgeber",
        lambda w, z: _in_liste(
            w, z, "/api/v1/organisationseinheiten?fuer_rolle=prozess_owner", w.int_id
        ),
        frozenset({GOVERNANCE, OWNER_FB, OWNER_INT}),
    ),
    Handlung(
        # Das Cockpit ist kein eigener Zugang, sondern dieselbe Sicht in
        # aggregierter Form: wer den Prozess nicht sieht, zaehlt ihn auch nicht.
        "cockpit_zeile",
        lambda w, z: _in_zeile(
            w, z, "/api/v1/cockpit/datenobjekte_ohne_kategorie", w.unkategorisiert
        ),
        # Diese Quelle haengt an keinem Prozess und an keinem Tool: sichtbar ist
        # sie nur ihrem Fachbereich und den global lesenden Rollen. Genau das
        # muss die Cockpit-Zeile abbilden — sie ist dieselbe Sicht, gezaehlt.
        GLOBAL_LESEND | {DATENOWNER},
    ),
)


# --- Die Pruefung -----------------------------------------------------------


def test_matrix_ist_vollstaendig() -> None:
    """Jede Handlung nennt nur bekannte Zugaenge — und keine Handlung fehlt.

    Eine Erwartung mit einem Tippfehler wuerde sonst stillschweigend zu „darf
    nicht" werden und die Pruefung wertlos machen.
    """
    bekannt = set(ZUGAENGE)
    for handlung in HANDLUNGEN:
        unbekannt = set(handlung.erlaubt) - bekannt
        assert not unbekannt, f"{handlung.name} nennt unbekannte Zugaenge: {unbekannt}"
    namen = [h.name for h in HANDLUNGEN]
    assert len(namen) == len(set(namen)), "Doppelte Handlungsnamen"
    # Keine Handlung darf allen oder niemandem erlaubt sein, ohne dass es
    # auffaellt: beides gibt es, aber es ist begruendungspflichtig.
    fuer_alle = {h.name for h in HANDLUNGEN if set(h.erlaubt) == bekannt}
    assert fuer_alle == {"technologiematrix_lesen"}, fuer_alle
    assert not [h for h in HANDLUNGEN if not h.erlaubt]


@pytest.mark.parametrize("zugang", ZUGAENGE)
@pytest.mark.parametrize("handlung", HANDLUNGEN, ids=lambda h: h.name)
def test_matrix(welt: Welt, handlung: Handlung, zugang: str) -> None:
    """Jede Zelle einmal: darf er, oder darf er nicht.

    Der Vergleich laeuft ueber „hat es geklappt", nicht ueber einen bestimmten
    Status — verweigert wird mit 403, und das ist die Aussage. Ein 404 oder 422
    waere hier ein Fehler und faellt als solcher auf, weil er auf der falschen
    Seite der Grenze landet.
    """
    status = handlung.ausfuehren(welt, zugang)
    erlaubt = zugang in handlung.erlaubt
    if erlaubt:
        assert status < 400, (
            f"{handlung.name}: {zugang} darf laut Sollzustand, bekommt aber {status}"
        )
    else:
        assert status == 403, f"{handlung.name}: {zugang} darf nicht, bekommt aber {status}"


def test_ohne_rolle_bleibt_alles_leer(welt: Welt) -> None:
    """Angemeldet und trotzdem ohne Zugriff ist ein Zustand, kein Fehler.

    Kein 500, kein 404 — leere Listen und ein klares Nein. Das ist die
    Erfahrung, die ein neuer Mitarbeiter am ersten Tag macht.
    """
    kopf = welt.kopf(OHNE_ROLLE)
    for pfad in ("/api/v1/prozesse", "/api/v1/tools", "/api/v1/datenobjekte"):
        antwort = welt.client.get(pfad, headers=kopf)
        assert antwort.status_code == 200
        assert antwort.json() == []
    assert welt.client.get("/api/v1/auth/me", headers=kopf).json()["rollen"] == []


def test_auditor_aendert_nichts(welt: Welt) -> None:
    """Die Rolle ist in ``NUR_LESEND``; keine Schreibregel darf sie je bejahen.

    Diese Zusage traegt die Pruefsicht: ein Auditor, der versehentlich etwas
    aendern koennte, waere als Auditor nicht mehr brauchbar.
    """
    schreibend = [h for h in HANDLUNGEN if h.name not in _LESENDE_HANDLUNGEN]
    assert schreibend, "Ohne schreibende Handlungen sagt dieser Test nichts"
    for handlung in schreibend:
        assert AUDITOR not in handlung.erlaubt, handlung.name
        assert handlung.ausfuehren(welt, AUDITOR) == 403, handlung.name


#: Die lesenden Handlungen — alles Uebrige veraendert etwas und ist damit fuer
#: den Auditor tabu.
_LESENDE_HANDLUNGEN = frozenset(
    {
        "prozess_liste",
        "prozess_detail",
        "fremdes_prozessobjekt",
        "tool_liste",
        "tool_detail",
        "fremdes_tool",
        "datenobjekt_liste",
        "datenobjekt_detail",
        "fremdes_datenobjekt",
        "datenobjekt_katalog",
        "technologiematrix_lesen",
        "nachweis_lesen",
        "nutzerverwaltung",
        "personen_im_bereich",
        "bereichsauswahl_prozessgeber",
        "cockpit_zeile",
    }
)


def test_dieselbe_rolle_zwei_bereiche(welt: Welt) -> None:
    """Die Haelfte der Regel, die am leichtesten vergessen wird.

    ``OWNER_FB`` und ``FREMDER`` tragen **dieselbe** Rolle. Der eine darf am
    Prozessobjekt des Vertriebs alles, der andere nichts — der Unterschied ist
    allein der Bereich (P-App-3).
    """
    pfad = f"/api/v1/prozesse/{welt.prozess}"
    assert welt.client.get(pfad, headers=welt.kopf(OWNER_FB)).status_code == 200
    assert welt.client.get(pfad, headers=welt.kopf(FREMDER)).status_code == 403
    for zugang, erwartet in ((OWNER_FB, 200), (FREMDER, 403)):
        antwort = welt.client.patch(pfad, json={"supplier": "X"}, headers=welt.kopf(zugang))
        assert antwort.status_code == erwartet


def test_derselbe_bereich_zwei_rollen(welt: Welt) -> None:
    """Und die andere Haelfte: gleicher Bereich, andere Rolle (R-7).

    ``TECHNIKER`` und ``DATENOWNER`` sind beide im Fachbereich Vertrieb. Der
    eine schreibt das Tool-Objekt und nicht die Quelle, der andere umgekehrt.
    Ein rollenblind gesammelter Bereich haette beiden beides gegeben.
    """
    tool = f"/api/v1/tools/{welt.tool}"
    quelle = f"/api/v1/datenobjekte/{welt.datenobjekt}"
    assert (
        welt.client.patch(
            tool, json={"beschreibung": "x"}, headers=welt.kopf(TECHNIKER)
        ).status_code
        == 200
    )
    assert (
        welt.client.patch(
            tool, json={"beschreibung": "x"}, headers=welt.kopf(DATENOWNER)
        ).status_code
        == 403
    )
    assert (
        welt.client.patch(
            quelle, json={"kategorie": "vertraulich"}, headers=welt.kopf(DATENOWNER)
        ).status_code
        == 200
    )
    assert (
        welt.client.patch(
            quelle, json={"kategorie": "intern"}, headers=welt.kopf(TECHNIKER)
        ).status_code
        == 403
    )
    # Und der Datenobjekt-Owner sieht das Tool nicht einmal.
    assert welt.client.get(tool, headers=welt.kopf(DATENOWNER)).status_code == 403


def test_rechte_am_objekt_stimmen_mit_den_routen_ueberein(welt: Welt) -> None:
    """Die Auskunft ``rechte`` und die Schreibregel muessen dasselbe sagen.

    Die Oberflaeche blendet nach ``rechte`` aus (E-53). Wichen die beiden
    voneinander ab, waere entweder eine Schaltflaeche zu sehen, die ins 403
    laeuft, oder eine fehlende, obwohl es ginge — und beides untergraebt das
    Vertrauen in die Anzeige.
    """
    for zugang in ZUGAENGE:
        antwort = welt.client.get(f"/api/v1/tools/{welt.tool}", headers=welt.kopf(zugang))
        if antwort.status_code != 200:
            continue
        rechte = antwort.json()["rechte"]
        geschrieben = welt.client.patch(
            f"/api/v1/tools/{welt.tool}", json={"beschreibung": "Probe"}, headers=welt.kopf(zugang)
        )
        assert rechte["bearbeiten"] == (geschrieben.status_code == 200), zugang

    for zugang in ZUGAENGE:
        antwort = welt.client.get(
            f"/api/v1/datenobjekte/{welt.datenobjekt}", headers=welt.kopf(zugang)
        )
        if antwort.status_code != 200:
            continue
        rechte = antwort.json()["rechte"]
        geschrieben = welt.client.patch(
            f"/api/v1/datenobjekte/{welt.datenobjekt}",
            json={"kategorie": "vertraulich"},
            headers=welt.kopf(zugang),
        )
        assert rechte["kategorisieren"] == (geschrieben.status_code == 200), zugang


def test_ein_tool_objekt_ohne_einheit_gibt_es_nicht(welt: Welt) -> None:
    """Der Anker ist Pflicht — und das ist keine Rechte-, sondern eine Gueltigkeitsfrage.

    Deshalb steht das hier und nicht in der Matrix: die Antwort ist 422, nicht
    403. Ein Tool-Objekt ohne Einheit gehoerte niemandem, waere nur den global
    lesenden Rollen sichtbar und haette keinen Bereich, an dem sich eine
    Berechtigung festmachen liesse (R-9).
    """
    for zugang in (GOVERNANCE, TECHNIKER, PLATTFORM):
        antwort = welt.client.post(
            "/api/v1/tools",
            json={"name": "Ohne Anker"},
            headers=welt.kopf(zugang),
        )
        assert antwort.status_code == 422, f"{zugang}: {antwort.status_code}"
        assert "Organisationseinheit" in antwort.json()["detail"]

    # Der Auditor kommt gar nicht erst bis zur Pruefung der Gueltigkeit: die
    # Rolle liest ausschliesslich, und das entscheidet sich vor der Route.
    assert (
        welt.client.post(
            "/api/v1/tools", json={"name": "Ohne Anker"}, headers=welt.kopf(AUDITOR)
        ).status_code
        == 403
    )


def test_wer_nur_liest_kommt_an_keiner_schreibenden_route_vorbei(welt: Welt) -> None:
    """Die Zusage aus A.15, zentral gezogen statt in jeder Regel einzeln.

    Sie stand bis AP-13 nur als Menge ``NUR_LESEND`` im Code, ohne dass sie
    jemand las — und ruhte damit darauf, dass keine positive Regel den Auditor
    trifft. Eine tat es doch (E-58). Jetzt entscheidet die Methode: was nicht
    liest, ist ihm verwehrt, gleich an welcher Route.
    """
    kopf = welt.kopf(AUDITOR)
    # Lesen geht ueberall, wo er sehen darf.
    assert welt.client.get("/api/v1/prozesse", headers=kopf).status_code == 200
    assert welt.client.get(f"/api/v1/tools/{welt.tool}", headers=kopf).status_code == 200
    assert welt.client.get("/api/v1/nachweis", headers=kopf).status_code == 200

    # Und keine veraendernde Methode kommt durch — auch nicht an Routen, die es
    # fuer ihn gar nicht gibt: die Sperre greift vor der Route.
    for methode, pfad, koerper in (
        ("post", "/api/v1/tools", {"name": "X", "organisationseinheit_id": welt.de_id}),
        ("patch", f"/api/v1/tools/{welt.tool}", {"beschreibung": "X"}),
        ("patch", f"/api/v1/prozesse/{welt.prozess}", {"supplier": "X"}),
        ("post", "/api/v1/datenobjekte", {"name": "X", "fachbereich_id": welt.fachbereich}),
        ("delete", f"/api/v1/tools/{welt.tool}", None),
        (
            "put",
            "/api/v1/technologiematrix/apps-script/K1",
            {"bewertung": "erfuellt", "begruendung": "x"},
        ),
    ):
        aufruf = getattr(welt.client, methode)
        antwort = (
            aufruf(pfad, json=koerper, headers=kopf) if koerper else aufruf(pfad, headers=kopf)
        )
        assert antwort.status_code == 403, f"{methode.upper()} {pfad}: {antwort.status_code}"
        assert "liest ausschließlich" in antwort.json()["detail"]
