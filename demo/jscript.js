// ── State ─────────────────────────────────────────────────
  let SERVER_URL = localStorage.getItem('metabot_url') || 'http://localhost:8001';
  let totalQueries = 0;
  let totalTables = 0;
  let isLoading = false;

  // ── Init ──────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('serverUrlInput').value = SERVER_URL;
    document.getElementById('serverUrlDisplay').textContent = SERVER_URL.replace('http://', '');
    checkHealth();
  });

  async function checkHealth() {
    const dot = document.getElementById('statusDot');
    const txt = document.getElementById('statusText');
    try {
      const resp = await fetch(`${SERVER_URL}/health`, { signal: AbortSignal.timeout(3000) });
      if (resp.ok) {
        dot.classList.remove('offline');
        txt.textContent = 'online';
      } else { throw new Error(); }
    } catch {
      dot.classList.add('offline');
      txt.textContent = 'offline';
    }
  }

  // ── Sending ───────────────────────────────────────────────
  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  }

  async function sendMessage() {
    const input = document.getElementById('inputBox');
    const question = input.value.trim();
    if (!question || isLoading) return;

    // Hide welcome
    const welcome = document.getElementById('welcome');
    if (welcome) welcome.remove();

    // Add user message
    addMessage('user', question);
    input.value = '';
    input.style.height = 'auto';

    // Show thinking
    const thinkId = addThinking();
    isLoading = true;
    document.getElementById('sendBtn').disabled = true;

    try {
      const resp = await fetch(`${SERVER_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
        signal: AbortSignal.timeout(120000)
      });

      removeThinking(thinkId);

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        addError(`Server error ${resp.status}: ${err.detail || 'Unknown error'}`);
        return;
      }

      const data = await resp.json();
      addBotMessage(data);

      // Update stats
      totalQueries++;
      totalTables += (data.tables_found || 0);
      document.getElementById('queryCount').textContent = totalQueries;
      document.getElementById('tableCount').textContent = totalTables;

    } catch (err) {
      removeThinking(thinkId);
      if (err.name === 'TimeoutError') {
        addError('Request timed out. Ollama may still be loading the model. Try again in a moment.');
      } else {
        addError(`Cannot reach MetaBot server at ${SERVER_URL}. Make sure uvicorn is running.`);
      }
    } finally {
      isLoading = false;
      document.getElementById('sendBtn').disabled = false;
      input.focus();
    }
  }

  // ── Message rendering ─────────────────────────────────────
  function addMessage(role, text) {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = `
      <div class="avatar ${role}-av">${role === 'user' ? 'U' : 'M'}</div>
      <div class="bubble"><div class="bubble-text">${escapeHtml(text)}</div></div>
    `;
    msgs.appendChild(div);
    scrollToBottom();
    return div;
  }

  function addBotMessage(data) {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'message bot';

    const toolClass = `tool-${data.tool_used || 'search'}`;
    const toolLabel = (data.tool_used || 'search').replace('_', ' ').toUpperCase();
    const tablesText = data.tables_found > 0 ? `· ${data.tables_found} table${data.tables_found !== 1 ? 's' : ''}` : '';

    div.innerHTML = `
      <div class="avatar bot-av">M</div>
      <div class="bubble">
        <div class="bubble-meta">
          <span class="tool-badge ${toolClass}">${toolLabel}</span>
          <span class="tables-count">${tablesText}</span>
        </div>
        <div class="bubble-text">${escapeHtml(data.answer)}</div>
      </div>
    `;
    msgs.appendChild(div);
    scrollToBottom();
  }

  function addThinking() {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'message bot';
    const id = 'think-' + Date.now();
    div.id = id;
    div.innerHTML = `
      <div class="avatar bot-av">M</div>
      <div class="bubble thinking">
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
        <span class="thinking-label">querying metadata + asking Ollama...</span>
      </div>
    `;
    msgs.appendChild(div);
    scrollToBottom();
    return id;
  }

  function removeThinking(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function addError(msg) {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'message bot';
    div.innerHTML = `
      <div class="avatar bot-av" style="background:#5a2020">M</div>
      <div class="error-bubble">${escapeHtml(msg)}</div>
    `;
    msgs.appendChild(div);
    scrollToBottom();
  }

  // ── Helpers ───────────────────────────────────────────────
  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/\n/g, '<br>');
  }

  function scrollToBottom() {
    const msgs = document.getElementById('messages');
    setTimeout(() => msgs.scrollTop = msgs.scrollHeight, 50);
  }

  function sendExample(btn) {
    const text = btn.innerText.trim().split('\n').pop().trim();
    document.getElementById('inputBox').value = text;
    sendMessage();
  }

  function useChip(chip) {
    document.getElementById('inputBox').value = chip.textContent;
    sendMessage();
  }

  // ── Config modal ──────────────────────────────────────────
  function openConfig() {
    document.getElementById('configModal').classList.add('open');
  }

  function closeConfig() {
    document.getElementById('configModal').classList.remove('open');
  }

  function saveConfig() {
    const url = document.getElementById('serverUrlInput').value.trim().replace(/\/$/, '');
    SERVER_URL = url;
    localStorage.setItem('metabot_url', url);
    document.getElementById('serverUrlDisplay').textContent = url.replace('http://', '');
    closeConfig();
    checkHealth();
  }

  // Close modal on overlay click
  document.getElementById('configModal').addEventListener('click', function(e) {
    if (e.target === this) closeConfig();
  });

  // Health check every 30s
  setInterval(checkHealth, 30000);