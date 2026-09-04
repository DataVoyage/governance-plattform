"""Die Governance-Szenarien — jedes einmal, keines zweimal.

Was der Bestand ohne diesen Schritt nicht zeigen könnte:

* **Die Erklärung des technischen Owners** (A.10.3) — bis hierher gab es nur
  die des Prozesseigners.
* **Ein Widerspruch**: ein Werkzeug meldet rot, seine Erklärung sagt „Rahmen
  eingehalten". Genau dafür gibt es die Cockpit-Zeile.
* **Ein abgelehntes Gate** — bisher wurde jedes freigegeben.
* **Ein aufgelöster Lenkungsvorgang**, und damit einer der drei Auswege aus
  A.13.6. Der zweite Vorgang bleibt offen, damit beide Zustände vorkommen.
* **Ein Governance-Alarm** aus einem Verbotstatbestand nach EU AI Act: die
  Bewertung bricht ab und erzeugt keine Einstufung, sondern eine Meldung.
* **Eine geänderte Technologiematrix und eine geänderte Einstellung** — beides
  Entscheidungen der Governance, die im Nachweis stehen müssen.
* **Eine bewegte Datenlage**: eine Antwort von damals steht neben einer
  Wirklichkeit von heute (A.8.4).
* **Ein ausgeschiedener Owner** — das Prozessobjekt trägt niemand mehr.
* **Ein inaktives Werkzeug** und **eine veraltete Attestierung**.
"""

from __future__ import annotations

from app.bestand.kontext import Kontext
from app.models.enums import (
    Aufloesungsart,
    Datenkategorie,
    GateStatus,
    GateTyp,
    Klassenbewertung,
    SelbstverpflichtungTyp,
)
from app.services import asset, erinnerung, gate, klassen, konfiguration, lenkung
from app.services import selbstverpflichtung as verpflichtung


def _aussagen(typ: SelbstverpflichtungTyp, tier: int | None, **abweichend: bool) -> dict:
    werte = {}
    for aussage in verpflichtung.verlangte_aussagen(typ, tier):
        bestaetigt = abweichend.get(aussage.id, True)
        werte[aussage.id] = {
            "bestaetigt": bestaetigt,
            "kommentar": "Im Lehrbestand bestätigt." if bestaetigt else "Bewusst offen gelassen.",
        }
    return werte


def erklaerungen(kontext: Kontext) -> None:
    """Die Erklärung des technischen Owners (A.10.3) — einmal tragend, einmal widersprüchlich."""
    toolowner = kontext.wer("toolowner")

    with kontext.aktion(vor_tagen=200, stunde=9):
        verpflichtung.abgeben(
            kontext.db,
            toolowner,
            typ=SelbstverpflichtungTyp.TECHNISCHER_OWNER,
            tool=kontext.tool("im_rahmen"),
            aussagen=_aussagen(SelbstverpflichtungTyp.TECHNISCHER_OWNER, 3),
        )

    # Der Widerspruch: das Werkzeug meldet später rot, die Erklärung sagt
    # „Rahmen eingehalten". Beides zusammen ist die Cockpit-Zeile — eine
    # Erklärung, die von der Messung überholt wurde.
    with kontext.aktion(vor_tagen=199, stunde=10):
        verpflichtung.abgeben(
            kontext.db,
            toolowner,
            typ=SelbstverpflichtungTyp.TECHNISCHER_OWNER,
            tool=kontext.tool("ausserhalb"),
            aussagen=_aussagen(SelbstverpflichtungTyp.TECHNISCHER_OWNER, 3),
        )


def entscheidungen(kontext: Kontext) -> None:
    """Ein abgelehntes Gate, ein aufgelöster Vorgang, Matrix und Einstellung."""
    governance = kontext.wer("governance")
    prozessowner = kontext.wer("prozessowner")

    # Ein abgelehntes Gate: die Erstfreigabe wird verweigert, mit Grund. Der
    # Prozess bleibt im Entwurf — genau dafür gibt es den Zustand.
    with kontext.aktion(vor_tagen=150, stunde=11):
        vorgang = gate.einreichen(
            kontext.db,
            prozessowner,
            kontext.prozess("unbewertet"),
            gate_typ=GateTyp.GATE_2,
            ausloeser="kritikalitaet_gestiegen",
            begruendung="Vorgriff auf eine geplante Erweiterung.",
        )
        gate.entscheiden(
            kontext.db,
            governance,
            vorgang,
            status=GateStatus.ABGELEHNT,
            kommentar=(
                "Abgelehnt: ohne Bewertung lässt sich der Rahmen nicht bestimmen. "
                "Erst bewerten, dann erneut einreichen."
            ),
        )

    # Ein aufgelöster Lenkungsvorgang — einer der drei Auswege aus A.13.6.
    # Der zweite Vorgang bleibt offen, damit beide Zustände vorkommen.
    zu_schliessen = lenkung.offener_vorgang(kontext.db, kontext.tool("zwei_kanten").id)
    if zu_schliessen is not None:
        with kontext.aktion(vor_tagen=10, stunde=9):
            asset.aendere_tool(
                kontext.db,
                kontext.wer("toolowner"),
                kontext.tool("zwei_kanten"),
                {"ausfuehrungsidentitaet": "benannter_dienst"},
            )
            lenkung.loese_auf(
                kontext.db, kontext.wer("toolowner"), zu_schliessen, art=Aufloesungsart.ANPASSEN
            )

    # Zwei Entscheidungen der Governance, die im Nachweis stehen müssen: ein
    # Feld der Technologiematrix und eine Einstellung.
    with kontext.aktion(vor_tagen=140, stunde=14):
        klassen.setze_feld(
            kontext.db,
            governance,
            "appsheet",
            "K9",
            bewertung=Klassenbewertung.NICHT_ERFUELLBAR,
            begruendung=(
                "AppSheet trägt kein eigenes Wiederanlaufkonzept; für K9 ist die "
                "Plattform nicht geeignet."
            ),
        )
        konfiguration.setze(kontext.db, "asset_inaktiv_tage", "120")


def stehender_verstoss(kontext: Kontext) -> None:
    """Ein zweites Schicht-2-Verbot, das **nicht** aufgelöst wird.

    Der erste Verstoß (geteiltes Konto) wird im Lenkungsvorgang abgestellt.
    Bliebe es dabei, trüge der fertige Bestand am Ende keinen einzigen — und
    genau der Zustand ist der, den man sehen will. Dieser hier bleibt stehen:
    dauerhaft gültige Zugangsdaten im Werkzeug, das zweite der sechs Verbote.
    """
    with kontext.aktion(vor_tagen=35, stunde=10):
        asset.aendere_tool(
            kontext.db,
            kontext.wer("toolowner"),
            kontext.tool("ausserhalb"),
            {"statische_zugangsdaten": True},
        )
        # Die beiden uebrigen selbst erkennbaren Verbote — an demselben
        # Werkzeug. Drei an einem sind kein Rauschen, sondern das Bild eines
        # vorgefundenen Altbestands: wo eines schiefliegt, liegen meist mehrere
        # schief. Und es spart drei Objekte.
        asset.attestiere(
            kontext.db,
            kontext.wer("toolowner"),
            kontext.tool("ausserhalb"),
            {
                "attest_entscheidung_ueber_personen": True,
                "attest_mensch_dazwischen": False,
                "attest_undeklarierte_quellen": True,
            },
        )

    # Die beiden Verbote, die in der Zielplattform geschehen. Seit E-64 werden
    # sie am Werkzeug **erklärt** statt in einer Meldung ausgewählt — danach
    # sieht die Anwendung sie wie die anderen vier.
    with kontext.aktion(vor_tagen=34, stunde=11):
        asset.aendere_tool(
            kontext.db,
            kontext.wer("toolowner"),
            kontext.tool("ohne_prozess"),
            {"daten_ins_offene_netz": True},
        )
        lenkung.melde_abweichung(
            kontext.db,
            kontext.wer("toolowner"),
            kontext.tool("ohne_prozess"),
            begruendung="Ein Export verlässt die freigegebene Infrastruktur.",
        )

    # Das sechste Verbot an einem Werkzeug, dessen Vorgang schon offen ist.
    # Damit zeigt der Bestand die Regel aus A.13.5: ein Schicht-2-Verstoß hebt
    # eine laufende Stufe 1 auf Stufe 2 — und zwar seit E-64, weil er in den
    # Daten steht, nicht weil ihn jemand noch einmal meldet.
    with kontext.aktion(vor_tagen=33, stunde=12) as wann:
        asset.aendere_tool(
            kontext.db,
            kontext.wer("toolowner"),
            kontext.tool("ausserhalb"),
            {"protokollierung_umgangen": True},
        )
        lenkung.eskaliere_faellige(kontext.db, jetzt=wann)


def datenlage_bewegt_sich(kontext: Kontext) -> None:
    """Eine Antwort von damals steht neben einer Wirklichkeit von heute.

    Die Quelle wird nachträglich höher eingeordnet. Die Bewertung bleibt, wie
    sie war — und das Cockpit sagt, dass sie sich auf eine Lage bezieht, die es
    nicht mehr gibt (A.8.4).
    """
    with kontext.aktion(vor_tagen=45, stunde=9):
        asset.aendere_datenobjekt(
            kontext.db,
            kontext.wer("datenowner"),
            kontext.datenobjekt("ohne_kategorie"),
            {
                "kategorie": Datenkategorie.PERSONENBEZOGEN,
                "beschreibung": (
                    "Die Ablage enthält Fahrtenbücher je Person — der Personenbezug "
                    "wurde nachträglich erkannt und eingeordnet."
                ),
            },
        )


def nachtraege(kontext: Kontext) -> None:
    """Ausgeschiedener Owner, inaktives Werkzeug, Erinnerungslauf."""
    from app.models.organisation import User
    from app.services import verwaltung

    # Der Owner scheidet aus. Sein Prozessobjekt trägt danach niemand mehr —
    # die erste Zeile des Cockpits, und im Betrieb der häufigste Grund dafür.
    with kontext.aktion(vor_tagen=8, stunde=16):
        ausgeschieden: User = kontext.person("ausgeschieden")
        verwaltung.aendere_user(
            kontext.db,
            kontext.wer("administrator"),
            ausgeschieden,
            ist_aktiv=False,
        )

    # Ein Werkzeug ohne Lebenszeichen: die Telemetrie meldet seit Monaten
    # nichts. Es ist nicht regelwidrig, sondern vermutlich vergessen.
    with kontext.aktion(vor_tagen=6, stunde=9):
        tool = kontext.tool("ohne_prozess")
        tool.letzte_aktivitaet_am = kontext.zeitpunkt(200)
        kontext.db.flush()

    # Der geplante Lauf, der im Betrieb täglich läuft.
    with kontext.aktion(vor_tagen=2, stunde=7):
        erinnerung.lauf(kontext.db)


def lenkungswege(kontext: Kontext) -> None:
    """Alle Auswege aus A.13.6 einmal — und der Abbruch daneben.

    Drei Auflösungen sind zulässig und keine vierte: *anpassen*, *Rahmen
    erweitern* (verlangt eine neue Bewertung), *stilllegen*. Dazu der Abbruch,
    der kein Ausweg ist, sondern der Weg für eine **Fehlmeldung** — und den
    ausschließlich die Governance geht.

    Ein Bestand mit nur einem aufgelösten Vorgang sagt über die anderen beiden
    nichts. Sie sind drei verschiedene Fälle, keine Wiederholung.
    """
    from app.bestand.bewertungen import antworten_aus_profil
    from app.services import ableitung
    from app.services import bewertung as bewertung_service

    governance = kontext.wer("governance")
    toolowner = kontext.wer("toolowner")

    # Gelb meldet niemand mehr: es ist der gerechnete Zustand eines Werkzeugs
    # ohne Prozesskante (E-64). Im Bestand traegt ihn „ohne_prozess" — genau
    # deshalb heisst es so.

    # Eine Fehlmeldung — die Governance bricht sie ab. Der Vorgang bleibt in
    # der Historie stehen; gelöscht wird nichts.
    with kontext.aktion(vor_tagen=70, stunde=10):
        lenkung.melde_abweichung(
            kontext.db,
            toolowner,
            kontext.tool("ohne_prozess"),
            begruendung="Vermuteter Zugriff außerhalb des Rahmens.",
        )
    fehlmeldung = lenkung.offener_vorgang(kontext.db, kontext.tool("ohne_prozess").id)
    if fehlmeldung is not None:
        with kontext.aktion(vor_tagen=68, stunde=11):
            lenkung.brich_ab(
                kontext.db,
                governance,
                fehlmeldung,
                kommentar="Fehlmeldung: der Zugriff war der eines anderen Werkzeugs.",
            )

    # Rahmen erweitern: die Abweichung war berechtigt, der Rahmen zu eng. Das
    # verlangt eine **neue Bewertung** — sonst wäre es ein Freibrief.
    with kontext.aktion(vor_tagen=50, stunde=9):
        lenkung.melde_abweichung(
            kontext.db,
            toolowner,
            kontext.tool("im_rahmen"),
            begruendung="Das Werkzeug braucht eine Quelle, die der Prozess nicht erklärt.",
        )
    zu_erweitern = lenkung.offener_vorgang(kontext.db, kontext.tool("im_rahmen").id)
    if zu_erweitern is not None:
        prozess = kontext.prozess("kette1")
        profil = {
            "ki": 0,
            "ds": 1,
            "mb": 0,
            "it": 1,
            "rg": 0,
            "ur": ableitung.leite_kritikalitaet_ab(prozess),
        }
        antworten = antworten_aus_profil(profil)
        with kontext.aktion(vor_tagen=48, stunde=10):
            neue = bewertung_service.speichere(
                kontext.db,
                kontext.wer("prozessowner"),
                prozess,
                antworten,
                begruendungen=dict.fromkeys(antworten, "Neubewertung zur Rahmenerweiterung."),
            )
            lenkung.loese_auf(
                kontext.db,
                toolowner,
                zu_erweitern,
                art=Aufloesungsart.RAHMEN_ERWEITERN,
                bewertung_id=neue.id,
            )

    # Stilllegen: der dritte Ausweg. Er setzt das Werkzeug auf ``inaktiv`` —
    # der einzige Weg, auf dem dieser Status entsteht.
    with kontext.aktion(vor_tagen=26, stunde=9):
        lenkung.melde_abweichung(
            kontext.db,
            toolowner,
            kontext.tool("ohne_attest"),
            begruendung="Läuft unter einem geteilten Konto und ist nicht attestiert.",
        )
    stillzulegen = lenkung.offener_vorgang(kontext.db, kontext.tool("ohne_attest").id)
    if stillzulegen is not None:
        with kontext.aktion(vor_tagen=24, stunde=11):
            lenkung.loese_auf(kontext.db, toolowner, stillzulegen, art=Aufloesungsart.STILLLEGEN)


def gate_in_pruefung(kontext: Kontext) -> None:
    """Ein Gate-Vorgang, den die Governance angenommen, aber nicht entschieden hat.

    Der Zwischenstand zwischen „eingereicht" und einer Entscheidung: jemand
    sieht ihn sich an. Ohne ihn wäre der Status unbelegt.
    """
    offen = gate.offener_vorgang(kontext.db, kontext.prozess("kette3").id, GateTyp.GATE_2)
    if offen is not None:
        with kontext.aktion(vor_tagen=55, stunde=15):
            gate.entscheiden(
                kontext.db,
                kontext.wer("governance"),
                offen,
                status=GateStatus.IN_PRUEFUNG,
                kommentar="In Prüfung: die Gegenstelle wird noch bestätigt.",
            )


def verbotstatbestand(kontext: Kontext) -> None:
    """Eine Bewertung, die nach EU AI Act abbricht (A.8.5, Schritt 1b).

    Es entsteht **keine** Einstufung, sondern ein Governance-Alarm. Das ist der
    einzige Weg, auf dem eine Bewertung ohne Ergebnis endet — und ein Bestand
    ohne ihn könnte nicht zeigen, dass es ihn gibt.
    """
    from app.bestand.bewertungen import antworten_aus_profil
    from app.services import bewertung as bewertung_service

    antworten = antworten_aus_profil({"ki": 0, "ds": 0, "mb": 0, "it": 0, "rg": 0, "ur": 0})
    antworten["1a"] = True  # Es ist KI im Spiel …
    antworten["1b"] = True  # … und sie erfüllt einen Verbotstatbestand.
    with kontext.aktion(vor_tagen=12, stunde=10):
        bewertung_service.speichere(
            kontext.db,
            kontext.wer("prozessowner"),
            kontext.prozess("unbewertet"),
            antworten,
            begruendungen=dict.fromkeys(antworten, "Zur Vorführung des Verbotstatbestands."),
        )
