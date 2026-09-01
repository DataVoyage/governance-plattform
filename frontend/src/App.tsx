import { Navigate, Outlet, Route, Routes } from 'react-router-dom';

import { STANDARDSPRACHE } from '@/i18n';
import { SprachAnbieter, useSprache } from '@/i18n/SprachKontext';
import { Layout } from '@/komponenten/Layout';
import { Anmeldung } from '@/seiten/Anmeldung';
import { BewertungsWizard } from '@/seiten/BewertungsWizard';
import { ProzessDetail } from '@/seiten/ProzessDetail';
import { ProzessFormular } from '@/seiten/ProzessFormular';
import { ProzessListe } from '@/seiten/ProzessListe';

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
          <Route path="prozesse/:id/bewertung" element={<BewertungsWizard />} />
        </Route>
        <Route path="*" element={<NichtGefunden />} />
      </Route>
      <Route path="*" element={<Navigate to={`/${STANDARDSPRACHE}/prozesse`} replace />} />
    </Routes>
  );
}
