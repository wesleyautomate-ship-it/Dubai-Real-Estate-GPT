import { create } from 'zustand';

const STORAGE_KEY = 'auth.session';

const readSession = () => {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (error) {
    console.warn('[auth] Failed to parse stored session', error);
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
};

const writeSession = (session) => {
  if (typeof window === 'undefined') return;
  if (!session || (!session.accessToken && !session.refreshToken)) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch (error) {
    console.warn('[auth] Failed to persist session', error);
  }
};

const clearStoredSession = () => {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(STORAGE_KEY);
};

const initialSession = readSession();

const useAuthStore = create((set, get) => ({
  user: initialSession?.user ?? null,
  accessToken: initialSession?.accessToken ?? null,
  refreshToken: initialSession?.refreshToken ?? null,
  expiresAt: initialSession?.expiresAt ?? null,
  status: 'idle',
  error: null,
  isAuthenticated: Boolean(initialSession?.accessToken),

  hydrate: () => {
    const session = readSession();
    if (!session) return;
    set({
      user: session.user ?? null,
      accessToken: session.accessToken ?? null,
      refreshToken: session.refreshToken ?? null,
      expiresAt: session.expiresAt ?? null,
      isAuthenticated: Boolean(session.accessToken),
    });
  },

  setStatus: (status) => set({ status }),
  setError: (error) => set({ error }),

  setUser: (user) => {
    const session = {
      accessToken: get().accessToken,
      refreshToken: get().refreshToken,
      expiresAt: get().expiresAt,
      user: user ?? null,
    };
    writeSession(session);
    set({ user: session.user, isAuthenticated: Boolean(session.accessToken) });
  },

  setSession: ({ accessToken, refreshToken, user, expiresAt }) => {
    const session = {
      accessToken: accessToken ?? null,
      refreshToken: refreshToken ?? null,
      expiresAt: expiresAt ?? null,
      user: user ?? get().user,
    };
    writeSession(session);
    set({
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
      expiresAt: session.expiresAt,
      user: session.user,
      isAuthenticated: Boolean(session.accessToken),
      error: null,
    });
  },

  clearSession: () => {
    clearStoredSession();
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      expiresAt: null,
      isAuthenticated: false,
      status: 'idle',
      error: null,
    });
  },

  getAuthHeaders: () => {
    const token = get().accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  },
}));

export default useAuthStore;
