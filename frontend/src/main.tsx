import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { App } from '@/App';
import { SitzungsAnbieter } from '@/zustand/Sitzung';
import '@/stil/token.css';
import '@/stil/marke-kaufland.css';
import '@/stil/basis.css';
import '@/ui/ui.css';
import '@/stil.css';

createRoot(document.getElementById('root') as HTMLElement).render(
  <StrictMode>
    <BrowserRouter
      basename={import.meta.env.BASE_URL}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <SitzungsAnbieter>
        <App />
      </SitzungsAnbieter>
    </BrowserRouter>
  </StrictMode>,
);
