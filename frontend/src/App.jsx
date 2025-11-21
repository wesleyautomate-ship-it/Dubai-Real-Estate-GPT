import { useEffect, useMemo, useRef, useState } from 'react';

const API_BASE = `${window.location.origin}/api`;
const SAMPLE_PROMPTS = [
  'Who owns 905 at Castleton?',
  'History for 905 in Castleton',
  'Show me properties in City Walk',
  'Properties in Marina',
];

const ANALYTICS_KEYWORDS = ['analytics', 'insights', 'stats', 'statistics', 'trend', 'volume', 'market'];

export default function App() {
  const [stats, setStats] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isProcessing, setProcessing] = useState(false);
  const [thinkingStep, setThinkingStep] = useState('');
  const [modelOptions, setModelOptions] = useState([]);
  const [selectedModel, setSelectedModel] = useState(localStorage.getItem('llmProvider') || 'openai');
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchStats();
    fetchModels();
  }, []);

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
      const response = await fetch(`${API_BASE}/stats`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Stats load failed', error);
    }
  }

  async function fetchModels() {
    try {
      const response = await fetch(`${API_BASE}/tools/models`);
      if (!response.ok) throw new Error('Failed to load models');
      const data = await response.json();
      setModelOptions(data.options || []);
      setSelectedModel(data.selected || 'openai');
      localStorage.setItem('llmProvider', data.selected || 'openai');
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
      const response = await fetch(`${API_BASE}/tools/models`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      });
      if (!response.ok) throw new Error('Model update failed');
      await fetchModels();
      setModelMenuOpen(false);
    } catch (error) {
      console.error(error);
    }
  }

  async function handleSend() {
    const query = input.trim();
    if (!query || isProcessing) return;

    setProcessing(true);
    setInput('');
    setThinkingStep('Analyzing query');
    addMessage('user', { text: query });

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
    } catch (error) {
      console.error(error);
      addMessage('assistant', { error: true, text: error.message || 'Something went wrong.' });
    } finally {
      setProcessing(false);
      setThinkingStep('');
    }
  }

  function addMessage(role, payload) {
    setMessages((prev) => [...prev, { role, ...payload }]);
  }

  async function parseQuery(query) {
    const response = await fetch(`${API_BASE}/tools/parse_query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    if (!response.ok) throw new Error('Failed to parse query');
    return response.json();
  }

  async function getCurrentOwner(entities) {
    const response = await fetch(`${API_BASE}/tools/current_owner`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(entities),
    });
    if (!response.ok) throw new Error('Owner lookup failed');
    return response.json();
  }

  async function getTransactionHistory(entities) {
    const response = await fetch(`${API_BASE}/tools/transaction_history`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(entities),
    });
    if (!response.ok) throw new Error('History lookup failed');
    return response.json();
  }

  async function getOwnerPortfolio(query) {
    const phoneMatch = query.match(/\d{5,}/);
    const response = await fetch(`${API_BASE}/tools/owner_portfolio`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: phoneMatch ? phoneMatch[0] : undefined, name: phoneMatch ? undefined : query }),
    });
    if (!response.ok) throw new Error('Portfolio lookup failed');
    return response.json();
  }

  async function getMarketInsights(entities, query) {
    const response = await fetch(`${API_BASE}/stats`);
    if (!response.ok) throw new Error('Failed to load analytics');
    const stats = await response.json();
    const scope =
      entities?.community || entities?.building || query.match(/in ([A-Za-z\s]+)/i)?.[1]?.trim() || 'Dubai portfolio';
    return { scope, ...stats };
  }

  async function semanticSearch(query) {
    const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&limit=12`);
    if (!response.ok) throw new Error('Search failed');
    return response.json();
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
            {stats.total_properties?.toLocaleString() || 0} properties • Updated{' '}
            {stats.last_update ? new Date(stats.last_update).toLocaleDateString() : 'recently'}
          </span>
        )}
      </header>

      <main className="chat-area">
        {showWelcome && <WelcomeCard onPromptClick={(prompt) => setInput(prompt)} />}
        <div className="messages" aria-live="polite">
          {messages.map((msg, index) => (
            <MessageBubble key={index} message={msg} />
          ))}
          {thinkingStep && <ThinkingBubble step={thinkingStep} />}
          <div ref={messagesEndRef} />
        </div>
      </main>

      <footer className="composer">
        <div className="composer-bar">
          <div className="input-wrapper">
            <div className="model-selector">
              <button
                type="button"
                className="model-button"
                onClick={() => setModelMenuOpen((prev) => !prev)}
                aria-expanded={modelMenuOpen}
                aria-label={`Selected model ${modelLabel}`}
              >
                <span className="model-icon">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 3v4" />
                    <path d="M12 17v4" />
                    <path d="M7 8v8" />
                    <path d="M17 8v8" />
                  </svg>
                </span>
              </button>
              {modelMenuOpen && (
                <div className="model-menu">
                  {modelOptions.map((option) => (
                    <button
                      key={option.provider}
                      disabled={option.available === false}
                      className={`model-option${option.provider === selectedModel ? ' active' : ''}`}
                      onClick={() => updateModel(option.provider)}
                    >
                      {option.label}
                      {option.available === false && ' (API key missing)'}
                    </button>
                  ))}
                </div>
              )}
            </div>
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
          <button key={prompt} onClick={() => onPromptClick(prompt)}>
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

function renderCard(type, data) {
  switch (type) {
    case 'ownership':
      return <OwnershipCard data={data} />;
    case 'history':
      return <HistoryCard data={data} />;
    case 'portfolio':
      return <PortfolioCard data={data} />;
    case 'analytics':
      return <AnalyticsCard data={data} />;
    case 'search':
    default:
      return <SearchResults data={data} />;
  }
}

function OwnershipCard({ data }) {
  if (!data?.found) {
    return (
      <div className="card">
        <h3>Owner not found</h3>
        <p>{data?.message || 'No property matched your request.'}</p>
      </div>
    );
  }

  const ownerName = data.owner_name || data.institutional_owner?.name || 'Unknown owner';
  const ownerPhone = data.owner_phone || data.institutional_owner?.phone || 'N/A';

  return (
    <div className="card">
      <h3>Current Owner</h3>
      <p className="muted">
        {data.unit} • {data.building || 'Unknown building'} • {data.community || 'Unknown community'}
      </p>
      <p>
        <strong>{ownerName}</strong>
      </p>
      <p>{ownerPhone}</p>
      {data.last_price && <p>Last price: AED {Math.round(data.last_price).toLocaleString()}</p>}
      {data.last_transaction_date && <p>Date: {new Date(data.last_transaction_date).toLocaleDateString()}</p>}
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
