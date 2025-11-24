import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { renderCard } from './components/ResultCards';
import useAuthStore from './store/authStore';
import useConversationStore from './store/conversationStore';
/**
 * @typedef {Object} SearchResultCard
 * @property {string} [unit]
 * @property {string} [building]
 * @property {string} [community]
 * @property {string} [owner_name]
 * @property {number} [price_aed]
 * @property {string} [snippet]
 */

/**
 * @typedef {Object} ApiMeta
 * @property {string} [request_id]
 * @property {string} [provider]
 * @property {number} [latency_ms]
 */

const API_BASE = `${window.location.origin}/api`;
const AUTH_ENABLED = import.meta.env.VITE_REQUIRE_AUTH === 'true';
const CONVERSATION_PAGE_SIZE = 20;
const CONVERSATION_MAX_RETRIES = 5;
const SAMPLE_PROMPTS = [
  'Who owns 905 at Adress sky views tower 2?',
  'History for 905 in forte 1',
  'Show me properties in burj views ',
  'Properties in Marina',
];

const extractData = (payload) => (payload && typeof payload === 'object' && 'data' in payload ? payload.data : payload);

const resolveErrorMessage = (payload, fallback) => {
  if (!payload || typeof payload !== 'object') return fallback;
  if (Array.isArray(payload.errors) && payload.errors.length) {
    return payload.errors[0]?.message || fallback;
  }
  if (typeof payload.message === 'string') {
    return payload.message;
  }
  if (typeof payload.error === 'string') {
    return payload.error;
  }
  return fallback;
};

const mapStoredMessage = (message) => {
  if (!message) return null;
  const metadata = message.metadata && typeof message.metadata === 'object' && !Array.isArray(message.metadata)
    ? message.metadata
    : {};
  const uiPayload = metadata.ui && typeof metadata.ui === 'object' ? metadata.ui : null;

  if (uiPayload) {
    return {
      role: message.role,
      ...uiPayload,
    };
  }

  const text = metadata.text || message.content || '';
  if (metadata.error) {
    return {
      role: message.role,
      error: true,
      text,
    };
  }

  return {
    role: message.role,
    text,
  };
};

const summarizeAssistantMessage = (intent, query, meta) => {
  const safeQuery = query.length > 60 ? `${query.slice(0, 57)}…` : query;
  switch (intent) {
    case 'search':
      return `Search results for "${safeQuery}" (${meta.total ?? 0} found)`;
    case 'ownership':
      return `Ownership lookup for "${safeQuery}"`;
    case 'history':
      return `Transaction history requested for "${safeQuery}"`;
    case 'portfolio':
      return `Owner portfolio insights for "${safeQuery}"`;
    case 'analytics':
      return `Market analytics shared for "${safeQuery}"`;
    default:
      return `Assistant responded to "${safeQuery}"`;
  }
};

const summarizeErrorMessage = (query, message) => {
  const safeQuery = query.length > 60 ? `${query.slice(0, 57)}…` : query;
  return `Request for "${safeQuery}" failed: ${message}`;
};

export default function App() {
  const [stats, setStats] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isProcessing, setProcessing] = useState(false);
  const [thinkingStep, setThinkingStep] = useState('');
  const [modelOptions, setModelOptions] = useState([]);
  const [selectedModel, setSelectedModel] = useState(localStorage.getItem('llmProvider') || 'openai');
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [, setLastLatencyMs] = useState(null);
  const [globalError, setGlobalError] = useState('');
  const messagesEndRef = useRef(null);
  const lastSendRef = useRef(0);
  const searchCacheRef = useRef({});
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [loadingConversationId, setLoadingConversationId] = useState(null);
  const conversationFetchStateRef = useRef({
    inFlight: false,
    failures: 0,
    locked: false,
  });
  const storeSlice = useAuthStore(
    useCallback(
      (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        expiresAt: state.expiresAt,
        authStatus: state.status,
        authError: state.error,
        hydrate: state.hydrate,
        setStatus: state.setStatus,
        setError: state.setError,
        setSession: state.setSession,
        setUser: state.setUser,
        clearSession: state.clearSession,
        getAuthHeaders: state.getAuthHeaders,
      }),
      [],
    ),
  );
  const conversationSlice = useConversationStore(
    useCallback(
      (state) => ({
        conversations: state.conversations,
        conversationsStatus: state.status,
        conversationsError: state.error,
        startConversationsLoading: state.startLoading,
        setConversationsSuccess: state.setSuccess,
        setConversationsFailure: state.setFailure,
        resetConversations: state.reset,
      }),
      [],
    ),
  );

  const noop = () => {};

  const {
    user,
    isAuthenticated,
    accessToken,
    refreshToken,
    expiresAt,
    authStatus,
    authError,
    hydrate,
    setStatus,
    setError,
    setSession,
    setUser,
    clearSession,
    getAuthHeaders,
  } = AUTH_ENABLED
    ? storeSlice
    : {
        user: null,
        isAuthenticated: true,
        accessToken: null,
        refreshToken: null,
        expiresAt: null,
        authStatus: 'disabled',
        authError: null,
        hydrate: noop,
        setStatus: noop,
        setError: noop,
        setSession: noop,
        setUser: noop,
        clearSession: noop,
        getAuthHeaders: () => ({}),
      };
  const {
    conversations,
    conversationsStatus,
    conversationsError,
    startConversationsLoading,
    setConversationsSuccess,
    setConversationsFailure,
  } = conversationSlice;
  const [authEmail, setAuthEmail] = useState(user?.email ?? '');
  const [authNotice, setAuthNotice] = useState('');

  const refreshAccessToken = useCallback(async () => {
    if (!AUTH_ENABLED || !refreshToken) return false;

    try {
      setStatus('refreshing');
      setError(null);

      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      let payload = null;
      if (response.status !== 204) {
        const text = await response.text();
        payload = text ? JSON.parse(text) : null;
      }

      if (!response.ok) {
        const message = resolveErrorMessage(payload, 'Unable to refresh session.');
        throw new Error(message);
      }

      const data = extractData(payload) || payload || {};
      setSession({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        expiresAt: data.expires_at,
        user: data.user,
      });
      if (data?.user?.email) {
        setAuthEmail(data.user.email);
      }
      setAuthNotice('Session refreshed');
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Session refresh failed.';
      setError(message);
      setAuthNotice('');
      clearSession();
      return false;
    } finally {
      setStatus('idle');
    }
  }, [clearSession, refreshToken, setError, setSession, setStatus]);

  const performRequest = useCallback(
    async (
      path,
      {
        method = 'GET',
        body,
        headers = {},
        auth = AUTH_ENABLED,
        retry = true,
      } = {},
    ) => {
      const requestHeaders = { ...headers };
      if (body && !('Content-Type' in requestHeaders)) {
        requestHeaders['Content-Type'] = 'application/json';
      }
      if (auth) {
        Object.assign(requestHeaders, getAuthHeaders());
      }

      const config = {
        method,
        headers: requestHeaders,
        body: body ? JSON.stringify(body) : undefined,
      };

      const response = await fetch(`${API_BASE}${path}`, config);

      if (AUTH_ENABLED && response.status === 401 && auth) {
        if (retry && refreshToken) {
          const refreshed = await refreshAccessToken();
          if (refreshed) {
            return performRequest(path, { method, body, headers, auth, retry: false });
          }
        }

        if (isAuthenticated) {
          clearSession();
          setAuthNotice('Session expired. Please sign in again.');
        }
      }

      let payload = null;
      if (response.status !== 204) {
        const text = await response.text();
        payload = text ? JSON.parse(text) : null;
      }

      if (!response.ok) {
        const message = resolveErrorMessage(payload, `Request failed (${response.status})`);
        const error = new Error(message);
        error.status = response.status;
        error.payload = payload;
        throw error;
      }

      return payload;
    },
    [
      clearSession,
      getAuthHeaders,
      isAuthenticated,
      refreshAccessToken,
      refreshToken,
      setAuthNotice,
    ],
  );

  const fetchConversations = useCallback(async () => {
    const state = conversationFetchStateRef.current;
    if (state.inFlight || state.locked) {
      return;
    }

    state.inFlight = true;

    try {
      let attempts = state.failures;
      startConversationsLoading(1);

      while (attempts < CONVERSATION_MAX_RETRIES) {
        try {
          const payload = await performRequest(`/conversations?limit=${CONVERSATION_PAGE_SIZE}`, {
            method: 'GET',
            auth: AUTH_ENABLED,
          });
          const data = extractData(payload) || {};
          const items = Array.isArray(data.conversations) ? data.conversations : [];
          const total = payload?.meta?.extra?.count;

          setConversationsSuccess({
            items,
            page: 1,
            pageSize: CONVERSATION_PAGE_SIZE,
            total: typeof total === 'number' ? total : undefined,
          });

          state.failures = 0;
          state.locked = false;
          return;
        } catch (error) {
          attempts += 1;
          state.failures = attempts;
          const baseMessage =
            error instanceof Error ? error.message : 'Failed to load conversations.';
          const isFinalAttempt = attempts >= CONVERSATION_MAX_RETRIES;
          const message = isFinalAttempt
            ? `${baseMessage} (stopped after ${CONVERSATION_MAX_RETRIES} attempts)`
            : `${baseMessage} (retrying ${attempts}/${CONVERSATION_MAX_RETRIES})`;

          setConversationsFailure(message);

          if (isFinalAttempt) {
            state.locked = true;
            return;
          }

          await new Promise((resolve) =>
            setTimeout(resolve, Math.min(1000, attempts * 250)),
          );
          startConversationsLoading(1);
        }
      }
    } finally {
      state.inFlight = false;
    }
  }, [
    performRequest,
    setConversationsFailure,
    setConversationsSuccess,
    startConversationsLoading,
  ]);

  const ensureConversation = useCallback(
    async (query) => {
      if (activeConversationId) {
        return activeConversationId;
      }

      try {
        const payload = await performRequest('/conversations', {
          method: 'POST',
          body: {
            title: query ? query.slice(0, 80) : undefined,
            metadata: { source: 'web', created_at: new Date().toISOString() },
          },
          auth: AUTH_ENABLED,
        });
        const data = extractData(payload) || {};
        const conversation = data.conversation || data;
        const conversationId = conversation?.id;
        if (conversationId) {
          setActiveConversationId(conversationId);
          await fetchConversations();
        }
        return conversationId;
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to start conversation.';
        throw new Error(message);
      }
    },
    [activeConversationId, fetchConversations, performRequest],
  );

  const appendConversationMessage = useCallback(
    async (conversationId, payload) => {
      if (!conversationId) return;
      try {
        await performRequest(`/conversations/${conversationId}/messages`, {
          method: 'POST',
          body: payload,
          auth: AUTH_ENABLED,
        });
      } catch (error) {
        console.warn('[conversation] Failed to persist message', error);
      }
    },
    [performRequest],
  );

  const handleSelectConversation = useCallback(
    async (conversationId) => {
      if (!conversationId || conversationId === activeConversationId) return;
      setLoadingConversationId(conversationId);
      try {
        const payload = await performRequest(`/conversations/${conversationId}`, {
          method: 'GET',
          auth: AUTH_ENABLED,
        });
        const data = extractData(payload) || {};
        const historyMessages = Array.isArray(data.messages) ? data.messages : [];
        const mapped = historyMessages
          .map(mapStoredMessage)
          .filter(Boolean);
        setMessages(mapped);
        setActiveConversationId(conversationId);
        setGlobalError('');
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to load conversation.';
        setGlobalError(message);
      } finally {
        setLoadingConversationId(null);
      }
    },
    [activeConversationId, performRequest],
  );

  const handleStartNewConversation = useCallback(() => {
    setActiveConversationId(null);
    setMessages([]);
    setStats(null);
    setThinkingStep('');
    setGlobalError('');
    setInput('');
  }, []);

  const focusEmailInput = useCallback(() => {
    const field = document.getElementById('auth-email-field');
    if (field) {
      field.focus();
      field.select();
    }
  }, []);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const handleSendMagicLink = useCallback(
    async (event) => {
      if (!AUTH_ENABLED) return;
      event?.preventDefault();
      const email = authEmail.trim();
      if (!email) {
        setError('Enter your email to receive a magic link.');
        return;
      }

      setStatus('magic-link');
      setError(null);
      setAuthNotice('');

      try {
        await performRequest('/auth/magic-link', {
          method: 'POST',
          body: {
            email,
            redirect_to: window.location.origin,
          },
          auth: false,
        });
        setAuthNotice('Magic link sent! Check your email to finish signing in.');
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Magic link request failed.';
        setError(message);
      } finally {
        setStatus('idle');
      }
    },
    [authEmail, performRequest, setError, setStatus],
  );

  const handleSignOut = useCallback(() => {
    if (!AUTH_ENABLED) return;
    clearSession();
    setMessages([]);
    setStats(null);
    setGlobalError('');
    setThinkingStep('');
    setAuthNotice('Signed out.');
  }, [clearSession]);

  const handleAuthEmailChange = useCallback(
    (value) => {
      if (!AUTH_ENABLED) return;
      setAuthEmail(value);
      if (authError) {
        setError(null);
      }
    },
    [authError, setError],
  );

  useEffect(() => {
    if (!AUTH_ENABLED) {
      return;
    }
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!AUTH_ENABLED) return;
    if (user?.email) {
      setAuthEmail(user.email);
    }
  }, [user]);

  useEffect(() => {
    if (!authNotice) {
      return undefined;
    }
    const timeout = window.setTimeout(() => setAuthNotice(''), 4000);
    return () => window.clearTimeout(timeout);
  }, [authNotice]);

  useEffect(() => {
    if (!AUTH_ENABLED) return;
    if (!isAuthenticated) {
      setMessages([]);
      setInput('');
      setThinkingStep('');
      setGlobalError('');
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (!AUTH_ENABLED || !accessToken) {
      return;
    }
    if (!accessToken) {
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        const payload = await performRequest('/auth/me');
        if (cancelled) return;
        const data = extractData(payload);
        if (data?.user) {
          setUser(data.user);
          if (data.user.email) {
            setAuthEmail(data.user.email);
          }
        }
      } catch (error) {
        console.error('Auth profile load failed', error);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [accessToken, performRequest, setUser]);

  useEffect(() => {
    if (!AUTH_ENABLED) {
      fetchStats();
      fetchModels();
      return;
    }

    if (!isAuthenticated) {
      setStats(null);
      return;
    }

    fetchStats();
    fetchModels();
  }, [isAuthenticated]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const handler = (event) => {
      if (!event.target.closest('.model-selector')) {
        setModelMenuOpen(false);
      }
    };
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, []);

  async function fetchStats() {
    try {
      const payload = await performRequest('/stats');
      const data = extractData(payload) || payload || null;
      setStats(data);
    } catch (error) {
      console.error('Stats load failed', error);
    }
  }

  async function fetchModels() {
    try {
      const payload = await performRequest('/tools/models');
      const data = extractData(payload) || payload || {};
      const options = (data.options || []).filter((opt) => opt.available !== false);
      setModelOptions(options);
      const selected = data.selected || (options[0]?.provider || 'openai');
      setSelectedModel(selected);
      localStorage.setItem('llmProvider', selected);
    } catch (error) {
      console.error('Model load failed', error);
      setModelOptions([]);
    }
  }

  const modelLabel = useMemo(() => {
    const option = modelOptions.find((opt) => opt.provider === selectedModel);
    return option ? option.label : selectedModel.toUpperCase();
  }, [modelOptions, selectedModel]);

  async function updateModel(provider) {
    if (provider === selectedModel) {
      setModelMenuOpen(false);
      return;
    }
    try {
      await performRequest('/tools/models', {
        method: 'POST',
        body: { provider },
      });
      await fetchModels();
      setModelMenuOpen(false);
    } catch (error) {
      console.error('Model update failed', error);
    }
  }

  async function handleSend() {
    const query = input.trim();
    if (!query || isProcessing) return;

    if (AUTH_ENABLED && !isAuthenticated) {
      setGlobalError('Sign in to start chatting.');
      focusEmailInput();
      return;
    }

    const now = performance.now();
    if (now - lastSendRef.current < 500) {
      return; // debounce rapid submits
    }
    lastSendRef.current = now;

    const started = performance.now();
    logEvent('send', { provider: selectedModel, query });
    setGlobalError('');
    setProcessing(true);
    setInput('');
    setThinkingStep('Analyzing query');
    addMessage('user', { text: query });

    let conversationId;
    try {
      conversationId = await ensureConversation(query);
      if (conversationId) {
        await appendConversationMessage(conversationId, {
          role: 'user',
          content: query,
          metadata: {
            text: query,
          },
        });
      }
    } catch (error) {
      console.error('Failed to ensure conversation', error);
      setGlobalError(error instanceof Error ? error.message : 'Unable to start conversation.');
    }

    try {
      const parsed = await parseQuery(query);
      let resolvedIntent = parsed.intent;
      if (resolvedIntent === 'search' && ANALYTICS_KEYWORDS.some((kw) => query.toLowerCase().includes(kw))) {
        resolvedIntent = 'analytics';
      }

      let result;
      if (resolvedIntent === 'ownership') {
        setThinkingStep('Finding owner');
        result = await getCurrentOwner(parsed.entities);
      } else if (resolvedIntent === 'history') {
        setThinkingStep('Loading history');
        result = await getTransactionHistory(parsed.entities);
      } else if (resolvedIntent === 'portfolio') {
        setThinkingStep('Fetching portfolio');
        result = await getOwnerPortfolio(query);
      } else if (resolvedIntent === 'analytics') {
        setThinkingStep('Calculating insights');
        result = await getMarketInsights(parsed.entities, query);
      } else {
        setThinkingStep('Running semantic search');
        result = await semanticSearch(query);
        resolvedIntent = 'search';
      }

      addMessage('assistant', { type: resolvedIntent, data: result });
      const meta = extractResultMeta(resolvedIntent, result);
      const latencyMs = Math.round(performance.now() - started);
      setLastLatencyMs(latencyMs);
      logEvent('result', {
        intent: resolvedIntent,
        provider: selectedModel,
        latency_ms: latencyMs,
        total: meta.total,
        found: meta.found,
        used_fallback: meta.used_fallback,
      });

      if (conversationId) {
        await appendConversationMessage(conversationId, {
          role: 'assistant',
          content: summarizeAssistantMessage(resolvedIntent, query, meta),
          metadata: {
            ui: {
              role: 'assistant',
              type: resolvedIntent,
              data: result,
            },
            intent: resolvedIntent,
            metrics: meta,
          },
        });
        await fetchConversations();
      }
    } catch (error) {
      console.error(error);
      logEvent('error', { provider: selectedModel, message: error.message || 'unknown', intent: 'unknown' });
      setGlobalError(error.message || 'Request failed.');
      addMessage('assistant', { error: true, text: error.message || 'Request failed.' });

      if (conversationId) {
        await appendConversationMessage(conversationId, {
          role: 'assistant',
          content: summarizeErrorMessage(query, error.message || 'Request failed.'),
          metadata: {
            ui: {
              role: 'assistant',
              error: true,
              text: error.message || 'Request failed.',
            },
            error: true,
            message: error.message || 'Request failed.',
          },
        });
        await fetchConversations();
      }
    } finally {
      setProcessing(false);
      setThinkingStep('');
    }
  }

  function addMessage(role, payload) {
    setMessages((prev) => [...prev, { role, ...payload }]);
  }

  function logEvent(name, payload) {
    console.info(`[ui] ${name}`, payload);
  }

  async function parseQuery(query) {
    const payload = await performRequest('/tools/parse_query', {
      method: 'POST',
      body: { query, provider: selectedModel },
    });
    return extractData(payload) || payload || {};
  }

  async function getCurrentOwner(entities) {
    const payload = await performRequest('/tools/current_owner', {
      method: 'POST',
      body: { ...entities, provider: selectedModel },
    });
    return extractData(payload) || payload || {};
  }

  async function getTransactionHistory(entities) {
    const payload = await performRequest('/tools/transaction_history', {
      method: 'POST',
      body: { ...entities, provider: selectedModel },
    });
    return extractData(payload) || payload || {};
  }

  async function getOwnerPortfolio(query) {
    const phoneMatch = query.match(/\d{5,}/);
    const payload = await performRequest('/tools/owner_portfolio', {
      method: 'POST',
      body: {
        phone: phoneMatch ? phoneMatch[0] : undefined,
        name: phoneMatch ? undefined : query,
        provider: selectedModel,
      },
    });
    return extractData(payload) || payload || {};
  }

  async function getMarketInsights(entities, query) {
    try {
      const payload = await performRequest('/stats');
      const statsData = extractData(payload) || payload || {};
      const scope =
        entities?.community || entities?.building || query.match(/in ([A-Za-z\s]+)/i)?.[1]?.trim() || 'Dubai portfolio';
      return { scope, ...statsData };
    } catch (error) {
      throw new Error('Failed to load analytics');
    }
  }

  async function semanticSearch(query) {
    const cacheKey = `${selectedModel}::${query}`;
    const cached = searchCacheRef.current[cacheKey];
    if (cached) {
      logEvent('search_cache_hit', { provider: selectedModel, query });
      return cached;
    }
    const payload = await performRequest(
      `/search?q=${encodeURIComponent(query)}&limit=12&provider=${encodeURIComponent(selectedModel)}`
    );
    const data = extractData(payload) || payload || {};
    searchCacheRef.current[cacheKey] = data;
    return data;
  }

  function extractResultMeta(intent, data) {
    if (!data) return { total: 0, found: false };
    switch (intent) {
      case 'search':
        return {
          total: data.total ?? (data.results ? data.results.length : 0),
          found: (data.total ?? 0) > 0 || (data.results || []).length > 0,
          used_fallback: data.used_fallback,
        };
      case 'ownership':
        return { total: data.found ? 1 : 0, found: !!data.found };
      case 'history': {
        const total = data.total_transactions ?? (data.history ? data.history.length : 0);
        return { total, found: total > 0 };
      }
      case 'portfolio': {
        const total = data.total_properties ?? (data.portfolio ? data.portfolio.length : 0);
        return { total, found: data.found ?? total > 0 };
      }
      case 'analytics':
        return { total: data.total_properties ?? 0, found: true };
      default:
        return { total: 0, found: false };
    }
  }

  const showWelcome = messages.length === 0;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="logo-mark">RE</div>
        <div>
          <h1>RealEstateGPT</h1>
          <p>Dubai Property Assistant</p>
        </div>
        {stats && (
          <span className="stat-chip">
            {(stats.total_properties ?? 0) > 0
              ? `${stats.total_properties?.toLocaleString()} properties`
              : 'Downtown test data'}
            {' · '}
            {stats.last_update ? new Date(stats.last_update).toLocaleDateString() : 'recently'}
          </span>
        )}
      </header>

      <div className="workspace">
        <aside className="conversation-panel" aria-label="Conversation history">
          <div className="conversation-header">
            <h2>Conversations</h2>
            <button type="button" onClick={handleStartNewConversation} className="conversation-new-btn">
              New
            </button>
          </div>
          {conversationsError && <p className="conversation-error">{conversationsError}</p>}
          {conversationsStatus === 'loading' && <p className="conversation-loading">Loading…</p>}
          {!conversations?.length && conversationsStatus === 'success' && !conversationsError && (
            <p className="conversation-empty">No conversations yet.</p>
          )}
          <ul className="conversation-list">
            {conversations.map((conversation) => {
              const isActive = conversation.id === activeConversationId;
              const subtitle = conversation.last_message_preview || 'Draft conversation';
              return (
                <li key={conversation.id}>
                  <button
                    type="button"
                    className={`conversation-item${isActive ? ' active' : ''}`}
                    onClick={() => handleSelectConversation(conversation.id)}
                    disabled={loadingConversationId === conversation.id}
                  >
                    <span className="conversation-title">{conversation.title || 'Untitled chat'}</span>
                    <span className="conversation-meta">{subtitle}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        <main className="chat-area">
          {AUTH_ENABLED && (
            <AuthPanel
              isAuthenticated={isAuthenticated}
              user={user}
              authEmail={authEmail}
              authStatus={authStatus}
              authError={authError}
              authNotice={authNotice}
              expiresAt={expiresAt}
              onEmailChange={handleAuthEmailChange}
              onSendMagicLink={handleSendMagicLink}
              onSignOut={handleSignOut}
            />
          )}
          {globalError && <ErrorBanner message={globalError} onClose={() => setGlobalError('')} />}
          {showWelcome && <WelcomeCard onPromptClick={(prompt) => setInput(prompt)} />}
          <div className="messages" aria-live="polite">
            {messages.map((msg, index) => (
              <MessageBubble key={index} message={msg} />
            ))}
            {thinkingStep && <ThinkingBubble step={thinkingStep} />}
            {isProcessing && <LoadingCard />}
            <div ref={messagesEndRef} />
          </div>
        </main>
      </div>

      <footer className="composer">
        <div className="composer-bar">
          <div className="input-wrapper">
            <ModelSelector
              modelLabel={modelLabel}
              modelMenuOpen={modelMenuOpen}
              modelOptions={modelOptions}
              selectedModel={selectedModel}
              onToggleMenu={() => setModelMenuOpen((prev) => !prev)}
              onSelect={updateModel}
            />
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about property ownership..."
              rows={1}
              disabled={isProcessing}
            />
          </div>
          <button className="send-btn" onClick={handleSend} disabled={!input.trim() || isProcessing}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </footer>
    </div>
  );
}

function WelcomeCard({ onPromptClick }) {
  return (
    <div className="welcome-card">
      <h2>Ask me anything about Dubai real estate</h2>
      <p>I can help you find property owners, transaction history, portfolios, and market insights.</p>
      <div className="chips">
        {SAMPLE_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => {
              console.info('[ui] prompt_click', { prompt });
              onPromptClick(prompt);
            }}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({ message }) {
  if (message.error) {
    return (
      <div className={`message ${message.role}`}>
        <div className="message-card error">{message.text}</div>
      </div>
    );
  }

  if (message.role === 'assistant' && message.type) {
    return (
      <div className="message assistant">
        <div className="message-card">{renderCard(message.type, message.data)}</div>
      </div>
    );
  }

  return (
    <div className={`message ${message.role}`}>
      <div className="message-card">{message.text}</div>
    </div>
  );
}

function ThinkingBubble({ step }) {
  return (
    <div className="message assistant">
      <div className="message-card thinking">
        <span className="spinner" aria-hidden="true" />
        <span>{step}...</span>
      </div>
    </div>
  );
}

function ErrorBanner({ message, onClose }) {
  if (!message) return null;
  return (
    <div className="error-banner">
      <span>{message}</span>
      <button type="button" onClick={onClose} aria-label="Dismiss error">
        ×
      </button>
    </div>
  );
}

function LoadingCard() {
  return (
    <div className="message assistant">
      <div className="message-card loading">
        <div className="skeleton-line wide" />
        <div className="skeleton-line" />
        <div className="skeleton-line short" />
      </div>
    </div>
  );
}

function ModelSelector({ modelLabel, modelMenuOpen, modelOptions, selectedModel, onToggleMenu, onSelect }) {
  return (
    <div className="model-selector">
      <button
        type="button"
        className="model-button"
        onClick={onToggleMenu}
        aria-expanded={modelMenuOpen}
        aria-label={`Selected model ${modelLabel}`}
      >
        <span className="model-dot" />
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 3v4" />
          <path d="M12 17v4" />
          <path d="M7 8v8" />
          <path d="M17 8v8" />
        </svg>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {modelMenuOpen && (
        <div className="model-menu">
          {modelOptions.map((option) => (
            <button
              key={option.provider}
              disabled={option.available === false}
              className={`model-option${option.provider === selectedModel ? ' active' : ''}`}
              onClick={() => onSelect(option.provider)}
            >
              {option.label}
              {option.available === false && ' (API key missing)'}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}


function HistoryCard({ data }) {
  if (!data?.history?.length) {
    return (
      <div className="card">
        <h3>Transaction History</h3>
        <p>No transaction history found.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>Transaction History</h3>
      <div className="timeline">
        {data.history.map((txn, index) => (
          <div key={`${txn.date}-${index}`} className="timeline-item">
            <div className="timeline-date">{new Date(txn.date).toLocaleDateString()}</div>
            <div>
              <p>
                AED {Math.round(txn.price || 0).toLocaleString()}{' '}
                {txn.price_per_sqft && `( ${Math.round(txn.price_per_sqft)} AED/sqft )`}
              </p>
              <p>Seller: {txn.seller_name || 'N/A'}</p>
              <p>Buyer: {txn.buyer_name || 'N/A'}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PortfolioCard({ data }) {
  if (!data?.found || !data.portfolio?.length) {
    return (
      <div className="card">
        <h3>Portfolio</h3>
        <p>{data?.message || 'No holdings found for that owner.'}</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>{data.owner_name || 'Owner'} Portfolio</h3>
      <p className="muted">
        {data.total_properties} properties • AED {Math.round(data.total_value || 0).toLocaleString()}
      </p>
      <div className="list">
        {data.portfolio.map((prop, index) => (
          <div key={`${prop.unit}-${index}`} className="list-item">
            <p>
              <strong>{prop.unit || 'Unit'}</strong> {prop.building && `• ${prop.building}`}
            </p>
            <p>{prop.community || 'Unknown community'}</p>
            {prop.last_price && <p>AED {Math.round(prop.last_price).toLocaleString()}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}

function AnalyticsCard({ data }) {
  if (!data) {
    return (
      <div className="card">
        <h3>Market Insights</h3>
        <p>No analytics available.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>Market Insights</h3>
      <p className="muted">{data.scope}</p>
      <div className="grid">
        <div>
          <p className="muted">Properties indexed</p>
          <p>{data.total_properties?.toLocaleString() || 0}</p>
        </div>
        <div>
          <p className="muted">Avg price/sqft</p>
          <p>AED {Math.round(data.avg_price_per_sqft || 0).toLocaleString()}</p>
        </div>
      </div>
    </div>
  );
}

function SearchResults({ data }) {
  if (!data?.results?.length) {
    return (
      <div className="card">
        <h3>No results</h3>
        <p>Try a different search or ask about a specific unit.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>Search Results</h3>
      <div className="list">
        {data.results.map((item, index) => (
          <div key={`${item.unit || index}-${index}`} className="list-item">
            <p>
              <strong>{item.unit || item.property_id || 'Unit'}</strong> {item.building && `• ${item.building}`}
            </p>
            <p>{item.community || 'Unknown community'}</p>
            {item.owner_name && <p>Owner: {item.owner_name}</p>}
            {item.price_aed && <p>Last price: AED {Math.round(item.price_aed).toLocaleString()}</p>}
            {item.snippet && <p className="muted">{item.snippet}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}

