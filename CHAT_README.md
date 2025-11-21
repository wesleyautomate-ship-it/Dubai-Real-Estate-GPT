# RealEstateGPT - Conversational Property Assistant

A conversation-first chat interface for Dubai real estate data, powered by your Supabase database and OpenAI embeddings.

## 🎯 What's Been Built

### Backend API Tools (`backend/api/chat_tools_api.py`)

**New Endpoints:**
- `/api/tools/parse_query` - Detects intent & extracts unit/building/community
- `/api/tools/resolve_alias` - Normalizes building/community names
- `/api/tools/current_owner` - Finds current property owner
- `/api/tools/transaction_history` - Gets full transaction timeline
- `/api/tools/owner_portfolio` - Shows all properties owned by person
- `/api/tools/export_csv` - Converts data to CSV

### Frontend Chat UI (`frontend/chat.html`)

**Features:**
- ✅ Responsive design (mobile-first, desktop two-pane)
- ✅ Conversation bubbles with message cards
- ✅ Quick intent chips (Ownership, History, Portfolio, Export)
- ✅ Example queries on welcome screen
- ✅ Desktop sidebar with threads & saved exports
- ✅ Mobile bottom navigation
- ✅ Auto-growing textarea composer
- ✅ Loading skeletons with shimmer

## 📋 What You Need to Complete

### 1. CSS Styling (`frontend/chat-style.css`)

Create a new file with the following structure:

```css
/* Base styles - Inter font, 14-16px body */
:root {
    --primary: #0E3A8A;
    --primary-hover: #1e40af;
    --bg-canvas: #ffffff;
    --bg-card: #F7F7F9;
    --text-primary: #1f2937;
    --text-secondary: #6b7280;
    --border: #e5e7eb;
    --radius: 12px;
    --shadow: 0 1px 3px rgba(0,0,0,0.1);
}

body {
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 15px;
    margin: 0;
    background: var(--bg-canvas);
}

/* Layout - Desktop two-pane, mobile single column */
.app-container {
    display: flex;
    height: 100vh;
}

.sidebar {
    width: 280px;
    background: var(--bg-card);
    border-right: 1px solid var(--border);
    padding: 16px;
}

.main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    max-width: 1040px;
    margin: 0 auto;
}

/* Header with stats pill */
.header {
    padding: 20px 24px;
    border-bottom: 1px solid var(--border);
}

.stats-pill {
    background: var(--bg-card);
    padding: 8px 16px;
    border-radius: 24px;
    font-size: 13px;
}

/* Chat messages */
.messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
}

.message {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
}

.message.user {
    flex-direction: row-reverse;
}

.message-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-center;
    font-size: 18px;
}

.message-content {
    max-width: 70%;
    background: var(--bg-card);
    padding: 14px 18px;
    border-radius: var(--radius);
}

/* Cards for ownership, history, etc. */
.ownership-card,
.history-card,
.list-card {
    background: white;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    box-shadow: var(--shadow);
}

/* Composer bar */
.composer-container {
    border-top: 1px solid var(--border);
    padding: 16px 24px;
}

.composer-bar {
    display: flex;
    gap: 12px;
    align-items: flex-end;
}

.message-input {
    flex: 1;
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 12px 16px;
    font-family: inherit;
    font-size: 15px;
    resize: none;
    max-height: 200px;
}

.send-btn {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: var(--primary);
    color: white;
    border: none;
    cursor: pointer;
}

.send-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

/* Quick intent chips */
.quick-intents {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
}

.intent-chip {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 20px;
    font-size: 14px;
    cursor: pointer;
}

/* Mobile responsive */
@media (max-width: 640px) {
    .desktop-only { display: none; }
    
    .message-content {
        max-width: 90%;
    }
    
    .composer-container {
        position: sticky;
        bottom: 0;
        background: white;
        padding-bottom: 80px; /* Space for nav */
    }
}

@media (min-width: 641px) {
    .mobile-only { display: none; }
}

/* Mobile bottom nav */
.mobile-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 64px;
    background: white;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-around;
}

.nav-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    border: none;
    background: none;
    font-size: 11px;
    color: var(--text-secondary);
}

.nav-item.active {
    color: var(--primary);
}

/* Loading skeleton */
.skeleton-card {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.skeleton-line {
    height: 16px;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 4px;
}

@keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* Welcome screen */
.welcome-screen {
    text-align: center;
    padding: 60px 20px;
}

.welcome-icon {
    font-size: 64px;
    margin-bottom: 24px;
}

.example-queries {
    margin-top: 32px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    justify-content: center;
}

.example-chip {
    padding: 12px 20px;
    background: white;
    border: 2px solid var(--border);
    border-radius: 24px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
}

.example-chip:hover {
    border-color: var(--primary);
    background: #f0f9ff;
}
```

### 2. JavaScript Implementation (`frontend/chat-script.js`)

Create the chat logic:

```javascript
// State management
let currentThread = null;
let messages = [];
let isProcessing = false;

// API Base URL
const API_BASE = window.location.origin + '/api';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeChat();
    loadStats();
    setupEventListeners();
});

function initializeChat() {
    // Load saved threads from localStorage
    const threads = JSON.parse(localStorage.getItem('chatThreads') || '[]');
    renderThreads(threads);
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();
        
        const statsText = `${data.total_properties?.toLocaleString() || 0} properties • Updated ${new Date().toLocaleDateString()}`;
        document.getElementById('statsText').textContent = statsText;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function setupEventListeners() {
    const input = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    
    // Auto-resize textarea
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = input.scrollHeight + 'px';
        sendBtn.disabled = !input.value.trim();
    });
    
    // Send on Enter (Shift+Enter for newline)
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) handleSend();
        }
    });
    
    // Send button
    sendBtn.addEventListener('click', handleSend);
    
    // Example queries
    document.querySelectorAll('.example-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            input.value = chip.dataset.query;
            input.dispatchEvent(new Event('input'));
            handleSend();
        });
    });
    
    // Intent chips
    document.querySelectorAll('.intent-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const intent = chip.dataset.intent;
            input.value = getIntentPrompt(intent);
            input.focus();
        });
    });
    
    // New chat
    document.getElementById('newChatBtn')?.addEventListener('click', startNewChat);
}

function getIntentPrompt(intent) {
    const prompts = {
        ownership: 'Who owns ',
        history: 'Show me the history for ',
        portfolio: 'What properties does ',
        export: 'Export data for '
    };
    return prompts[intent] || '';
}

async function handleSend() {
    const input = document.getElementById('messageInput');
    const query = input.value.trim();
    
    if (!query || isProcessing) return;
    
    isProcessing = true;
    input.value = '';
    input.style.height = 'auto';
    document.getElementById('sendBtn').disabled = true;
    
    // Hide welcome screen
    document.getElementById('welcomeScreen')?.remove();
    
    // Add user message
    addMessage('user', query);
    
    // Add loading indicator
    const loadingId = addLoadingMessage();
    
    try {
        // Parse query to detect intent
        const parseResponse = await fetch(`${API_BASE}/tools/parse_query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        
        const parsed = await parseResponse.json();
        
        // Route to appropriate tool
        let result;
        if (parsed.intent === 'ownership') {
            result = await getCurrentOwner(parsed.entities);
        } else if (parsed.intent === 'history') {
            result = await getTransactionHistory(parsed.entities);
        } else if (parsed.intent === 'portfolio') {
            result = await getOwnerPortfolio(query);
        } else {
            // Fallback to semantic search
            result = await semanticSearch(query);
        }
        
        // Remove loading, add result
        removeLoadingMessage(loadingId);
        renderResult(result, parsed.intent);
        
    } catch (error) {
        removeLoadingMessage(loadingId);
        addMessage('assistant', `Sorry, I encountered an error: ${error.message}`);
    } finally {
        isProcessing = false;
    }
}

async function getCurrentOwner(entities) {
    if (!entities.unit) {
        return { error: true, message: 'Please specify a unit number' };
    }
    
    const response = await fetch(`${API_BASE}/tools/current_owner`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(entities)
    });
    
    return await response.json();
}

async function getTransactionHistory(entities) {
    const response = await fetch(`${API_BASE}/tools/transaction_history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(entities)
    });
    
    return await response.json();
}

async function semanticSearch(query) {
    const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&limit=12`);
    return await response.json();
}

function addMessage(role, content) {
    const container = document.getElementById('messagesContainer');
    const message = document.createElement('div');
    message.className = `message ${role}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
    message.appendChild(avatar);
    message.appendChild(contentDiv);
    container.appendChild(message);
    
    scrollToBottom();
}

function addLoadingMessage() {
    const template = document.getElementById('loadingTemplate');
    const loading = template.content.cloneNode(true);
    const loadingId = 'loading-' + Date.now();
    loading.firstElementChild.id = loadingId;
    
    document.getElementById('messagesContainer').appendChild(loading);
    scrollToBottom();
    
    return loadingId;
}

function removeLoadingMessage(id) {
    document.getElementById(id)?.remove();
}

function renderResult(result, intent) {
    const container = document.getElementById('messagesContainer');
    const message = document.createElement('div');
    message.className = 'message assistant';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '🤖';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    if (result.error) {
        content.textContent = result.message;
    } else if (intent === 'ownership') {
        content.appendChild(createOwnershipCard(result));
    } else if (intent === 'history') {
        content.appendChild(createHistoryCard(result));
    } else {
        content.appendChild(createSearchResults(result));
    }
    
    message.appendChild(avatar);
    message.appendChild(content);
    container.appendChild(message);
    
    scrollToBottom();
}

function createOwnershipCard(data) {
    const card = document.createElement('div');
    card.className = 'ownership-card';
    card.innerHTML = `
        <h3>Current Owner</h3>
        <div class="property-info">
            <p><strong>${data.unit}</strong> • ${data.building || ''} • ${data.community}</p>
        </div>
        <div class="owner-info">
            <p><strong>Owner:</strong> ${data.owner_name}</p>
            <p><strong>Phone:</strong> 
                <a href="https://wa.me/${data.owner_phone?.replace(/\D/g, '')}" target="_blank">
                    ${data.owner_phone}
                </a>
            </p>
            ${data.last_price ? `<p><strong>Last Price:</strong> AED ${data.last_price?.toLocaleString()}</p>` : ''}
            ${data.last_transaction_date ? `<p><strong>Date:</strong> ${data.last_transaction_date}</p>` : ''}
        </div>
    `;
    return card;
}

function createHistoryCard(data) {
    const card = document.createElement('div');
    card.className = 'history-card';
    
    let html = `<h3>Transaction History - ${data.unit}</h3>`;
    
    if (data.history && data.history.length > 0) {
        html += '<div class="timeline">';
        data.history.forEach(txn => {
            html += `
                <div class="timeline-item">
                    <div class="timeline-date">${txn.date}</div>
                    <div class="timeline-content">
                        <p><strong>AED ${txn.price?.toLocaleString()}</strong></p>
                        <p>Seller: ${txn.seller_name}</p>
                        <p>Buyer: ${txn.buyer_name}</p>
                    </div>
                </div>
            `;
        });
        html += '</div>';
    } else {
        html += '<p>No transaction history found.</p>';
    }
    
    card.innerHTML = html;
    return card;
}

function createSearchResults(data) {
    const card = document.createElement('div');
    card.className = 'list-card';
    
    if (data.results && data.results.length > 0) {
        card.innerHTML = `
            <h3>Found ${data.total} properties</h3>
            <div class="results-list">
                ${data.results.map(r => `
                    <div class="result-item">
                        <p><strong>${r.unit} - ${r.building || r.community}</strong></p>
                        <p>${r.owner_name} • ${r.owner_phone}</p>
                        ${r.price_aed ? `<p>AED ${r.price_aed?.toLocaleString()}</p>` : ''}
                    </div>
                `).join('')}
            </div>
        `;
    } else {
        card.innerHTML = '<p>No results found. Try a different query.</p>';
    }
    
    return card;
}

function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    container.scrollTop = container.scrollHeight;
}

function startNewChat() {
    messages = [];
    document.getElementById('messagesContainer').innerHTML = '';
    location.reload(); // Simple approach - reload to show welcome
}
```

### 3. Routing Update (`backend/main.py`)

Add a route to serve the chat page:

```python
@app.get("/chat")
async def serve_chat():
    """Serve chat interface"""
    chat_path = frontend_path / "chat.html"
    if chat_path.exists():
        return FileResponse(chat_path)
    return {"message": "Chat interface not found"}
```

## 🚀 Running the Chat App

1. **Ensure server is running:**
   ```bash
   python run_server.py
   ```

2. **Access the chat interface:**
   ```
   http://localhost:8787/chat
   ```

3. **Test queries:**
   - "Who owns 905 at Seven Palm?"
   - "History for 1203 in Serenia Living"
   - "Show me properties in Dubai Marina"

## 📱 Mobile Features

- Sticky composer at bottom
- Large touch targets (44px minimum)
- One-tap WhatsApp integration (`wa.me/` links)
- Bottom navigation for Threads/Saved/Settings
- Responsive cards and messages

## 🎨 Customization

- **Colors:** Edit CSS variables in `:root`
- **Fonts:** Change Inter to your preferred font
- **Cards:** Add new card types in `renderResult()`
- **Intents:** Add more in `parse_natural_query()`

## ⚠️ Current Limitations

1. **No authentication yet** - Add Supabase Auth for multi-user
2. **Thread persistence** - Currently uses localStorage, should use database
3. **CMA generation** - Endpoint exists but needs implementation
4. **Top investors** - Need to add this RPC function

## 📝 Next Steps

1. Complete CSS styling file
2. Add chat route to main.py
3. Test on mobile device
4. Add authentication
5. Implement thread storage in Supabase
6. Add export functionality
7. Build CMA report generator

---

**Built with ❤️ for Dubai Real Estate**
