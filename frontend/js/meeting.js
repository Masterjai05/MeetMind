const API = 'http://127.0.0.1:5000';

// Get meeting ID from URL (?id=1)
const meetingId = new URLSearchParams(window.location.search).get('id');

if (!meetingId) {
  window.location.href = 'index.html';
}

// ── LOAD MEETING DETAILS ──
async function loadMeeting() {
  try {
    const res = await fetch(`${API}/meetings/${meetingId}`);
    const meeting = await res.json();

    if (!res.ok) {
      alert('Meeting not found.');
      window.location.href = 'index.html';
      return;
    }

    // Header
    document.title = `MeetMind — ${meeting.title}`;
    document.getElementById('meetingTitle').textContent = meeting.title;
    document.getElementById('meetingDate').textContent = formatDate(meeting.created_at);

    const statusEl = document.getElementById('meetingStatus');
    statusEl.textContent = meeting.status;
    statusEl.className = `badge ${meeting.status}`;

    // If still processing — poll and refresh
    if (meeting.status !== 'done' && meeting.status !== 'failed') {
      document.getElementById('summaryText').textContent = 'Still processing... refresh in a moment.';
      document.getElementById('summaryText').classList.add('processing');
      setTimeout(loadMeeting, 5000);
      return;
    }

    // Summary
    document.getElementById('summaryText').textContent = meeting.summary || 'No summary available.';
    document.getElementById('summaryText').classList.remove('processing');

    // Action Items
    const actionList = document.getElementById('actionItemsList');
    const actions = safeParseJSON(meeting.action_items);
    if (actions.length > 0) {
      actionList.innerHTML = actions.map(a => `<li>${a}</li>`).join('');
    } else {
      actionList.innerHTML = '<p class="empty-list">No action items found.</p>';
    }

    // Decisions
    const decisionsList = document.getElementById('decisionsList');
    const decisions = safeParseJSON(meeting.decisions);
    if (decisions.length > 0) {
      decisionsList.innerHTML = decisions.map(d => `<li>${d}</li>`).join('');
    } else {
      decisionsList.innerHTML = '<p class="empty-list">No decisions found.</p>';
    }

    // Transcript
    document.getElementById('transcriptText').textContent =
      meeting.transcript || 'No transcript available.';

  } catch (err) {
    console.error(err);
    alert('Could not load meeting. Is Flask running?');
  }
}

// ── LOAD CHAT HISTORY ──
async function loadChatHistory() {
  try {
    const res = await fetch(`${API}/meetings/${meetingId}/chat`);
    const messages = await res.json();

    if (messages.length === 0) return;

    const container = document.getElementById('chatMessages');
    container.innerHTML = '';

    messages.forEach(m => {
      addBubble(m.role, m.message);
    });

    scrollChat();
  } catch (err) {
    console.error(err);
  }
}

// ── SEND CHAT MESSAGE ──
async function sendMessage() {
  const input = document.getElementById('chatInput');
  const question = input.value.trim();
  if (!question) return;

  input.value = '';

  // Show user message immediately
  addBubble('user', question);

  // Show thinking indicator
  const thinkingId = 'thinking-' + Date.now();
  addBubble('thinking', 'Thinking...', thinkingId);
  scrollChat();

  try {
    const res = await fetch(`${API}/meetings/${meetingId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });

    const data = await res.json();

    // Remove thinking bubble
    const thinkingEl = document.getElementById(thinkingId);
    if (thinkingEl) thinkingEl.remove();

    if (!res.ok) {
      addBubble('assistant', `Error: ${data.error}`);
    } else {
      addBubble('assistant', data.answer);
    }

    scrollChat();

  } catch (err) {
    const thinkingEl = document.getElementById(thinkingId);
    if (thinkingEl) thinkingEl.remove();
    addBubble('assistant', 'Failed to get answer. Check if Flask is running.');
    scrollChat();
  }
}

// ── HELPERS ──
function addBubble(role, text, id) {
  const container = document.getElementById('chatMessages');
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = text;
  if (id) bubble.id = id;
  container.appendChild(bubble);
}

function scrollChat() {
  const container = document.getElementById('chatMessages');
  container.scrollTop = container.scrollHeight;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleString();
}

function safeParseJSON(str) {
  try {
    const parsed = JSON.parse(str);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

// ── INIT ──
loadMeeting();
loadChatHistory();
