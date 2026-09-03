"""Ein vollstaendiger Datenbestand fuer eine Einzelhandelsgruppe.

Die Anwendung laesst sich mit drei Prozessobjekten bedienen, aber nicht
beurteilen. Erst ein Bestand, der einen ganzen Unternehmensbereich abbildet,
zeigt, ob die Oberflaeche traegt: ob das Cockpit Zeilen mit Inhalt hat, ob die
Tier-Verteilung eine Kurve statt eines Balkens ist, ob der Nachweis nach etwas
aussieht, das eine Pruefung liest.

Dieses Modul baut genau das. Zehn Fachbereiche einer Handelsgruppe mit ihren
Landesgesellschaften, die Menschen darin, ihre Datenobjekte, Prozesse und
Werkzeuge — und die Vorgaenge, die daran haengen: Bewertungen, Gates,
Selbstverpflichtungen, Rahmenabweichungen, Lenkungsvorgaenge.

**Drei Regeln tragen den Bestand.**

1. *Keine Testsignaturen.* Kein Name, kein Datenobjekt, kein Prozess traegt
   eine Kennung, die ihn als erfunden ausweist. Wer die Oberflaeche sieht,
   sieht eine Handelsgruppe bei der Arbeit.
2. *Alles entsteht ueber die Fachlogik.* Kein Datensatz wird an den Diensten
   vorbei geschrieben. Jede Bewertung laeuft durch den Baum, jede Frist durch
   ``arbeitstage_addieren``, jede Schreibaktion durch die
   Berechtigungspruefung — und zwar unter der Kennung des Menschen, der sie im
   Betrieb taete. Damit ist der Aufbau zugleich der schaerfste Integrationstest,
   den es hier gibt: was fachlich nicht geht, entsteht auch nicht.
3. *Die Zeitachse ist echt.* Ein Bestand, in dem alles in derselben Minute
   entstanden ist, sieht auf jedem Zeitverlauf aus wie ein einzelner Balken.
   Deshalb traegt jeder Vorgang seinen Zeitpunkt, und der Aufbau datiert
   zurueck (siehe ``kontext.Kontext.aktion``).

Aufruf::

    python -m app.bestand --leeren

Das ist destruktiv und deshalb ausdruecklich anzufordern. Ohne ``--leeren``
laeuft der Aufbau nur auf einer leeren Datenbank.
"""

from app.bestand.aufbau import Bericht, baue

__all__ = ["Bericht", "baue"]
