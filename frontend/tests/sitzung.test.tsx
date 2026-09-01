/**
 * Sitzung, Anmeldung und API-Client.
 */

import { renderHook, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ApiFehler, anfrage } from '@/api/client';
import { useSitzung } from '@/zustand/Sitzung';
import { EINHEITEN, PROFIL, fetchAttrappe, prozess, zeichne } from './hilfen';

describe('Anmeldung', () => {
  it('leitet ohne Token auf die Anmeldemaske', async () => {
    fetchAttrappe([]);
    zeichne('/de/prozesse', false);
    expect(await screen.findByRole('heading', { name: 'Anmeldung' })).toBeInTheDocument();
  });

  it('meldet an und zeigt danach die Prozessliste', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/dev-token', methode: 'POST', koerper: { access_token: 'tok' } },
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    ]);
    zeichne('/de/anmeldung', false);
    await userEvent.type(await screen.findByLabelText('Kennung'), 'sub-1');
    await userEvent.type(screen.getByLabelText('Name'), 'Olivia Owner');
    await userEvent.click(screen.getByRole('button', { name: 'Anmelden' }));
    expect(await screen.findByRole('heading', { name: 'Prozessobjekte' })).toBeInTheDocument();
    expect(window.localStorage.getItem('governance.token')).toBe('tok');
  });

  it('meldet eine fehlgeschlagene Anmeldung', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/dev-token', methode: 'POST', status: 404, koerper: {} },
    ]);
    zeichne('/de/anmeldung', false);
    await userEvent.type(await screen.findByLabelText('Kennung'), 'sub-1');
    await userEvent.click(screen.getByRole('button', { name: 'Anmelden' }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('leitet eine bestehende Sitzung von der Anmeldemaske weg', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/prozesse', koerper: [] },
      { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    ]);
    zeichne('/de/anmeldung');
    expect(await screen.findByRole('heading', { name: 'Prozessobjekte' })).toBeInTheDocument();
  });

  it('meldet ab und kehrt zur Anmeldemaske zurueck', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/prozesse', koerper: [] },
      { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    ]);
    zeichne('/de/prozesse');
    await userEvent.click(await screen.findByRole('button', { name: 'Abmelden' }));
    expect(await screen.findByRole('heading', { name: 'Anmeldung' })).toBeInTheDocument();
    expect(window.localStorage.getItem('governance.token')).toBeNull();
  });

  it('verwirft ein Token, das der Server nicht mehr akzeptiert', async () => {
    fetchAttrappe([{ pfad: '/api/v1/auth/me', status: 401, koerper: {} }]);
    zeichne('/de/prozesse');
    await waitFor(() => expect(window.localStorage.getItem('governance.token')).toBeNull());
    expect(await screen.findByRole('heading', { name: 'Anmeldung' })).toBeInTheDocument();
  });
});

describe('useSitzung', () => {
  it('kennt die Rollen des Profils', async () => {
    fetchAttrappe([{ pfad: '/api/v1/auth/me', koerper: PROFIL }]);
    window.localStorage.setItem('governance.token', 'tok');
    const { SitzungsAnbieter } = await import('@/zustand/Sitzung');
    const { result } = renderHook(() => useSitzung(), { wrapper: SitzungsAnbieter });
    await waitFor(() => expect(result.current.profil).not.toBeNull());
    expect(result.current.hatRolle('prozess_owner')).toBe(true);
    expect(result.current.hatRolle('governance')).toBe(false);
  });

  it('wirft ausserhalb des Anbieters', () => {
    const stille = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => renderHook(() => useSitzung())).toThrow(/SitzungsAnbieter/);
    stille.mockRestore();
  });

  it('kommt ohne verfuegbaren Speicher aus', async () => {
    const original = window.localStorage.getItem;
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('kein Speicher');
    });
    const { leseToken } = await import('@/zustand/Sitzung');
    expect(leseToken()).toBeNull();
    Storage.prototype.getItem = original;
  });
});

describe('API-Client', () => {
  it('gibt bei 204 nichts zurueck', async () => {
    fetchAttrappe([{ pfad: '/leer', status: 204, koerper: null }]);
    await expect(anfrage('/leer')).resolves.toBeUndefined();
  });

  it('uebernimmt die Fehlermeldung des Servers', async () => {
    fetchAttrappe([{ pfad: '/kaputt', status: 422, koerper: { detail: 'So nicht' } }]);
    await expect(anfrage('/kaputt')).rejects.toThrow('So nicht');
  });

  it('uebernimmt die erste Meldung einer Validierungsliste', async () => {
    fetchAttrappe([
      { pfad: '/felder', status: 422, koerper: { detail: [{ msg: 'Feld fehlt' }] } },
    ]);
    await expect(anfrage('/felder')).rejects.toThrow('Feld fehlt');
  });

  it('faellt auf den Status zurueck, wenn keine Meldung kommt', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('kein JSON');
        },
      })) as unknown as typeof fetch,
    );
    await expect(anfrage('/leer')).rejects.toThrow('HTTP 500');
  });

  it('haengt das Token an, wenn eines vorliegt', async () => {
    const { aufrufe, attrappe } = fetchAttrappe([{ pfad: '/mit-token', koerper: {} }]);
    await anfrage('/mit-token', { token: 'abc' });
    expect(aufrufe).toHaveLength(1);
    expect(attrappe.mock.calls[0][1]?.headers).toMatchObject({ Authorization: 'Bearer abc' });
  });

  it('kennzeichnet Fehler mit dem Status', () => {
    const fehler = new ApiFehler(403, 'verboten');
    expect(fehler.status).toBe(403);
    expect(fehler.name).toBe('ApiFehler');
  });
});

describe('Unbekannte Route', () => {
  it('zeigt eine Nicht-gefunden-Seite innerhalb der Sprachvariante', async () => {
    fetchAttrappe([{ pfad: '/api/v1/auth/me', koerper: PROFIL }]);
    zeichne('/de/gibt-es-nicht');
    expect(
      await screen.findByRole('heading', { name: 'Diese Seite gibt es nicht' }),
    ).toBeInTheDocument();
  });

  it('leitet die Wurzel auf die Standardsprache', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/prozesse', koerper: [] },
      { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    ]);
    zeichne('/');
    expect(await screen.findByRole('heading', { name: 'Prozessobjekte' })).toBeInTheDocument();
  });
});
