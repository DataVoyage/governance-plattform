"""Zwei Fachbereiche, elf Zugänge — mehr braucht es nicht.

**Logistik** ist der eigene Bereich: dort liegt alles, was geprüft wird, und
dort sitzen die fünf bereichsgebundenen Zugänge. **Personal** ist das
Gegenüber: ein zweiter Fachbereich mit eigenen Objekten, den niemand aus der
Logistik sehen darf. Ohne dieses Gegenüber ließe sich keine einzige negative
Aussage prüfen.

Die Logistik hat eine INT-Einheit und zwei Länder. Zwei, nicht eines: die
Reichweite steigt nach A.4.4 erst ab der zweiten Umsetzung, und ein Bestand
ohne zweites Land könnte das nicht zeigen.
"""

from __future__ import annotations

from app.bestand.kontext import Kontext, Unstimmig
from app.models.enums import Ebene, Rolle, ScopeTyp
from app.models.organisation import Fachbereich, Organisationseinheit, Rollenzuweisung, User
from app.services import klassen, konfiguration
from app.services.changelog import protokolliere_erstellung

DOMAENE = "beispiel-ag.de"

#: Der Erstzugang. Wie im Betrieb: das erste Subject bekommt die Startrollen,
#: ohne die niemand Rollen vergeben könnte. Er ist **nicht** einer der
#: Demo-Zugänge: er trägt App-Administrator **und** Governance zugleich, und
#: damit ließe sich an ihm keine der beiden Rollen für sich zeigen.
ERSTZUGANG = "erstzugang"

#: (Schlüssel, Anzeigename, Ländercodes)
FACHBEREICHE: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("logistik", "Logistik", ("DE", "FR")),
    ("personal", "Personal", ()),
)

#: Die Zugänge. Das mittlere Feld ist **Erläuterung, kein Anzeigename**: als
#: Name trägt jeder Zugang seine eigene Kennung.
#:
#: Das ist keine Kosmetik. Die Anmeldung übernimmt den Namen aus der Identität
#: (Architektur 10.1) — wer sich mit „prozessowner" in beiden Feldern anmeldet,
#: überschreibt damit einen abweichenden Namen im Bestand. Derselbe Mensch
#: erschiene dann je nach Ansicht unter zwei Namen: hier als „Prozess-Owner,
#: ganze Logistik", dort als „prozessowner". Kennung gleich Name schließt das
#: aus, und deshalb steht die Erläuterung im Code und in
#: ``docs/demo-zugaenge.md`` statt im Datensatz.
#:
#: Fünf davon liegen im **selben** Fachbereich. Verteilt man sie über
#: verschiedene Bereiche, sieht jeder etwas anderes, und man kann nicht
#: unterscheiden, ob der Unterschied von der Rolle oder vom Bereich kommt.
#: Nebeneinander zeigen sie beide Hälften der Regel (P-App-3).
#: (Kennung, Erläuterung, Rollen)
ZUGAENGE: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("governance", "Governance, unternehmensweit", ("governance@global",)),
    ("plattform", "Plattformbetrieb, unternehmensweit", ("plattform@global",)),
    ("auditor", "Auditor, unternehmensweit, nur lesend", ("auditor@global",)),
    ("administrator", "App-Administrator, unternehmensweit", ("app_administrator@global",)),
    ("prozessowner", "Prozess-Owner, ganze Logistik", ("prozess_owner@fb:logistik",)),
    ("bereichsowner", "Prozess-Owner, nur Logistik DE", ("prozess_owner@oe:logistik-de",)),
    ("prozessumsetzer", "Prozess-Umsetzer, Logistik DE", ("prozess_umsetzer@oe:logistik-de",)),
    ("toolowner", "Technischer Owner, ganze Logistik", ("technischer_owner@fb:logistik",)),
    ("datenowner", "Datenobjekt-Owner, ganze Logistik", ("datenobjekt_owner@fb:logistik",)),
    # Das Gegenüber: dieselbe Rolle, anderer Fachbereich. An ihm zeigt sich,
    # dass eine Rolle allein nichts trägt.
    ("fremdowner", "Prozess-Owner, Fachbereich Personal", ("prozess_owner@fb:personal",)),
    ("ohnerolle", "Angemeldet, ohne jede Rollenzuweisung", ()),
    # Traegt ein Prozessobjekt und scheidet spaeter aus. Kein Demo-Zugang: an
    # ihm zeigt sich die Cockpit-Zeile „Prozesse ohne tragenden Owner", und ein
    # deaktivierter Zugang liesse sich nicht mehr zum Anmelden benutzen.
    (
        "ausgeschieden",
        "Ausgeschieden — trägt sein Objekt nicht mehr",
        ("prozess_owner@fb:logistik",),
    ),
)


def _bereich(kontext: Kontext, angabe: str) -> tuple[ScopeTyp, object]:
    if angabe == "global":
        return ScopeTyp.GLOBAL, None
    art, _, schluessel = angabe.partition(":")
    if art == "fb":
        return ScopeTyp.FACHBEREICH, kontext.fachbereich(schluessel).id
    if art == "oe":
        return ScopeTyp.ORGANISATIONSEINHEIT, kontext.einheit(schluessel).id
    raise Unstimmig(f"Unbekannte Bereichsangabe: {angabe}")


def baue(kontext: Kontext) -> None:
    """Legt Erstzugang, Organisation und die elf Zugänge an."""
    db = kontext.db

    with kontext.aktion(vor_tagen=400):
        admin = User(
            subject=ERSTZUGANG,
            email=f"{ERSTZUGANG}@{DOMAENE}",
            name=ERSTZUGANG,
        )
        db.add(admin)
        db.flush()
        kontext.personen[ERSTZUGANG] = admin
        for rolle in (Rolle.APP_ADMINISTRATOR, Rolle.GOVERNANCE):
            zuweisung = Rollenzuweisung(user_id=admin.id, rolle=rolle, scope_typ=ScopeTyp.GLOBAL)
            db.add(zuweisung)
            db.flush()
            protokolliere_erstellung(
                db,
                zuweisung,
                akteur_user_id=admin.id,
                beschreibung="Startrolle des Erstzugangs (GP_BOOTSTRAP_ADMIN_SUBJECTS)",
            )

    with kontext.aktion(vor_tagen=395):
        for schluessel, name, laender in FACHBEREICHE:
            fachbereich = Fachbereich(name=name, code=f"fb-{schluessel}")
            db.add(fachbereich)
            db.flush()
            protokolliere_erstellung(db, fachbereich, akteur_user_id=admin.id)
            kontext.fachbereiche[schluessel] = fachbereich

            int_einheit = Organisationseinheit(fachbereich_id=fachbereich.id, ebene=Ebene.INT)
            db.add(int_einheit)
            db.flush()
            protokolliere_erstellung(db, int_einheit, akteur_user_id=admin.id)
            kontext.einheiten[schluessel] = int_einheit

            for land in laender:
                einheit = Organisationseinheit(
                    fachbereich_id=fachbereich.id, ebene=Ebene.LAND, land_code=land
                )
                db.add(einheit)
                db.flush()
                protokolliere_erstellung(db, einheit, akteur_user_id=admin.id)
                kontext.einheiten[f"{schluessel}-{land.lower()}"] = einheit

    with kontext.aktion(vor_tagen=390):
        for kennung, _erlaeuterung, _rollen in ZUGAENGE:
            if kennung == ERSTZUGANG:
                continue
            # Der Name **ist** die Kennung — sonst überschreibt ihn die erste
            # Anmeldung, und derselbe Mensch erscheint unter zwei Namen.
            nutzer = User(subject=kennung, email=f"{kennung}@{DOMAENE}", name=kennung)
            db.add(nutzer)
            db.flush()
            protokolliere_erstellung(db, nutzer, akteur_user_id=admin.id)
            kontext.personen[kennung] = nutzer

    with kontext.aktion(vor_tagen=389):
        for kennung, _erlaeuterung, rollen in ZUGAENGE:
            if kennung == ERSTZUGANG:
                continue
            for angabe in rollen:
                rolle, _, bereich = angabe.partition("@")
                scope_typ, scope_id = _bereich(kontext, bereich)
                zuweisung = Rollenzuweisung(
                    user_id=kontext.person(kennung).id,
                    rolle=Rolle(rolle),
                    scope_typ=scope_typ,
                    scope_id=scope_id,
                )
                db.add(zuweisung)
                db.flush()
                protokolliere_erstellung(db, zuweisung, akteur_user_id=admin.id)
    kontext.vergiss_rollen()


def stammdaten(kontext: Kontext) -> None:
    """Technologiematrix und Einstellungen — die Regelwerke, die sonst fehlen.

    Beide legen die Dienste beim ersten Zugriff selbst an. Hier geschieht das
    ausdrücklich, damit der Bestand vollständig ist und nicht erst beim ersten
    Aufruf einer Seite entsteht.
    """
    with kontext.aktion(vor_tagen=388):
        klassen.initialisiere(kontext.db)
        konfiguration.initialisiere(kontext.db)
