import { Navigate, Outlet, Route, Routes } from 'react-router-dom';

import { STANDARDSPRACHE } from '@/i18n';
import { SprachAnbieter, useSprache } from '@/i18n/SprachKontext';
import { Layout } from '@/komponenten/Layout';
import { Anmeldung } from '@/seiten/Anmeldung';
import { BewertungsWizard } from '@/seiten/BewertungsWizard';
import { Cockpit, CockpitZeileAnsicht } from '@/seiten/Cockpit';
import { DatenobjektDetail } from '@/seiten/DatenobjektDetail';
import { DatenobjektListe } from '@/seiten/DatenobjektListe';
import { Gates } from '@/seiten/Gates';
import { Klassen } from '@/seiten/Klassen';
import { Konzept } from '@/seiten/Konzept';
import { Konfiguration } from '@/seiten/Konfiguration';
import { Nachweis } from '@/seiten/Nachweis';
import { Lenkung } from '@/seiten/Lenkung';
import { ProzessDetail } from '@/seiten/ProzessDetail';
import { ProzessFormular } from '@/seiten/ProzessFormular';
import { ProzessListe } from '@/seiten/ProzessListe';
import { SelbstverpflichtungSeite } from '@/seiten/Selbstverpflichtung';
import { Stilprobe } from '@/seiten/Stilprobe';
import { Verwaltung } from '@/seiten/Verwaltung';
import { ToolDetail } from '@/seiten/ToolDetail';
import { ToolListe } from '@/seiten/ToolListe';

export function NichtGefunden() {
  const { t } = useSprache();
  return <h1>{t('app.nichtGefunden')}</h1>;
}

/** Haelt den Sprachkontext ueber allen Kindrouten dieser Sprachvariante. */
function SprachRahmen() {
  return (
    <SprachAnbieter>
      <Outlet />
    </SprachAnbieter>
  );
}

/**
 * Routen. Jede Sprachvariante liegt unter einem Landeskuerzel im Pfad
 * (Architektur 9.2); der Pfad steuert die Anzeige, nie die Berechtigung.
 */
export function App() {
  return (
    <Routes>
      <Route path="/:sprache" element={<SprachRahmen />}>
        <Route index element={<Navigate to="prozesse" replace />} />
        <Route path="anmeldung" element={<Anmeldung />} />
        <Route element={<Layout />}>
          <Route path="prozesse" element={<ProzessListe />} />
          <Route path="prozesse/neu" element={<ProzessFormular />} />
          <Route path="prozesse/:id" element={<ProzessDetail />} />
          <Route path="prozesse/:id/bearbeiten" element={<ProzessFormular />} />
          <Route path="prozesse/:id/bewertung" element={<BewertungsWizard />} />
          <Route
            path="prozesse/:id/selbstverpflichtung"
            element={<SelbstverpflichtungSeite gegenstand="prozess" />}
          />
          {/* Die Erklärung des technischen Owners nach A.10.3 war über die
              Oberfläche gar nicht erreichbar — sie bekommt ihren Weg dort, wo
              das Objekt steht, das sie betrifft. */}
          <Route
            path="tools/:id/selbstverpflichtung"
            element={<SelbstverpflichtungSeite gegenstand="tool" />}
          />
          <Route path="cockpit" element={<Cockpit />} />
          <Route path="cockpit/:schluessel" element={<CockpitZeileAnsicht />} />
          <Route path="gates" element={<Gates />} />
          <Route path="lenkung" element={<Lenkung />} />
          {/* Nachschlagewerk und Entscheidungsgrundlage in einem: die zehn
              Klassen aus A.9.2 und die Matrix aus Teil C.1. */}
          <Route path="klassen" element={<Klassen />} />
          {/* Das Vorgehen erklärt sich dort, wo damit gearbeitet wird. */}
          <Route path="konzept" element={<Konzept />} />
          {/* Fristen, Schwellen und Vorlauf sind Governance-Inhalt, keine
              Betriebsparameter (Architektur 6.6). Der Server prüft die
              Rolle noch einmal — der Pfad steuert die Anzeige, nie die
              Berechtigung. */}
          <Route path="konfiguration" element={<Konfiguration />} />
          {/* Verwaltung und Nachweis machen die Anwendung selbsttragend:
              Rollen wurden bisher nur über die API vergeben, und das
              Änderungsprotokoll war nur über die Datenbank zu lesen. */}
          <Route path="verwaltung" element={<Verwaltung />} />
          <Route path="nachweis" element={<Nachweis />} />
          <Route path="tools" element={<ToolListe />} />
          <Route path="tools/:id" element={<ToolDetail />} />
          <Route path="datenobjekte" element={<DatenobjektListe />} />
          <Route path="datenobjekte/:id" element={<DatenobjektDetail />} />
          <Route path="stilprobe" element={<Stilprobe />} />
        </Route>
        <Route path="*" element={<NichtGefunden />} />
      </Route>
      <Route path="*" element={<Navigate to={`/${STANDARDSPRACHE}/prozesse`} replace />} />
    </Routes>
  );
}
