const API = 'http://127.0.0.1:5000';

let selectedFile  = null;
let speakerCount  = 0;
const SPEAKER_LETTERS = 'ABCDEFGHIJ';

// ── SPEAKER NAME FIELDS ──
function addSpeaker() {
  if (speakerCount >= 10) {
    alert('Maximum 10 speakers supported.');
    return;
  }

  const letter    = SPEAKER_LETTERS[speakerCount];
  const container = document.getElementById('speakerNamesContainer');

  const row    = document.createElement('div');
  row.id       = `speaker-row-${letter}`;
  row.style.cssText = 'display:flex; gap:8px; margin-bottom:8px; align-items:center;';
  row.innerHTML = `
    <span style="width:80px; font-size:13px; color:#666; flex-shrink:0;">Speaker ${letter}:</span>
    <input
      type="text"
      id="speaker-${letter}"
      placeholder="Enter name (e.g. ${getDefaultName(speakerCount)})"
      style="flex:1; padding:6px 10px; border:1px solid #ddd; border-radius:6px; font-size:13px;"
    />
    <button
      type="button"
      onclick="removeSpeaker('${letter}')"
      style="padding:4px 10px; border:1px solid #ffcccc; background:#fff5f5; border-radius:6px; font-size:12px; cursor:pointer; color:#cc0000; flex-shrink:0;"
    >Remove</button>
  `;

  container.appendChild(row);
  speakerCount++;
}

function removeSpeaker(letter) {
  const row = document.getElementById(`speaker-row-${letter}`);
  if (row) row.remove();
  speakerCount = document.getElementById('speakerNamesContainer').children.length;
}

function getSpeakerNames() {
  const names = {};
  document.querySelectorAll('[id^="speaker-"]').forEach(input => {
    const letter = input.id.replace('speaker-', '');
    const name   = input.value.trim();
    if (name) names[letter] = name;
  });
  return names;
}

function getDefaultName(index) {
  const defaults = ['Priya', 'Arjun', 'Ravi', 'Meera', 'Kiran', 'Ananya', 'Raj', 'Divya', 'Amit', 'Sara'];
  return defaults[index] || `Person ${index + 1}`;
}

// ── FILE SELECTION ──
document.getElementById('fileInput').addEventListener('change', function () {
  selectedFile = this.files[0];
  document.getElementById('selectedFile').textContent = selectedFile
    ? `Selected: ${selectedFile.name}`
    : '';
});

// ── DRAG & DROP ──
const dropZone = document.getElementById('dropZone');

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  selectedFile = e.dataTransfer.files[0];
  document.getElementById('selectedFile').textContent = `Selected: ${selectedFile.name}`;
});

dropZone.addEventListener('click', () => {
  document.getElementById('fileInput').click();
});

// ── UPLOAD FILE ──
async function uploadFile() {
  if (!selectedFile) {
    showStatus('Please select a file first.', 'error');
    return;
  }

  const title        = document.getElementById('meetingTitle').value.trim() || 'Untitled Meeting';
  const speakerNames = getSpeakerNames();
  const btn          = document.getElementById('uploadBtn');

  btn.disabled    = true;
  btn.textContent = 'Uploading...';

  const formData = new FormData();
  formData.append('audio', selectedFile);
  formData.append('title', title);
  formData.append('speaker_names', JSON.stringify(speakerNames));

  try {
    showStatus('Uploading file...', 'info');

    const res  = await fetch(`${API}/upload`, { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) {
      showStatus(`Error: ${data.error}`, 'error');
      return;
    }

    const namesSummary = Object.keys(speakerNames).length > 0
      ? ` Speakers: ${Object.entries(speakerNames).map(([k,v]) => `${k}→${v}`).join(', ')}`
      : ' No speaker names provided — using Speaker A, B...';

    showStatus(`Uploaded! Processing "${data.title}".${namesSummary}`, 'info');
    pollStatus(data.meeting_id);
    loadMeetings();

  } catch (err) {
    showStatus('Upload failed. Make sure the Flask server is running.', 'error');
    console.error(err);
  } finally {
    btn.disabled    = false;
    btn.textContent = 'Upload & Process';
  }
}

// ── POLL STATUS ──
async function pollStatus(meetingId) {
  const interval = setInterval(async () => {
    try {
      const res  = await fetch(`${API}/meetings/${meetingId}/status`);
      const data = await res.json();

      if (data.status === 'transcribing') {
        showStatus('Transcribing audio... this takes a few minutes.', 'info');
      } else if (data.status === 'summarizing') {
        showStatus('Transcription done! Now summarizing with AI...', 'info');
      } else if (data.status === 'done') {
        showStatus('Done! Your meeting is ready.', 'success');
        clearInterval(interval);
        loadMeetings();
      } else if (data.status === 'failed') {
        showStatus('Processing failed. Check your API key in .env file.', 'error');
        clearInterval(interval);
      }
    } catch (err) {
      clearInterval(interval);
    }
  }, 5000);
}

// ── LOAD MEETINGS ──
async function loadMeetings() {
  const container = document.getElementById('meetingsList');

  try {
    const res      = await fetch(`${API}/meetings`);
    const meetings = await res.json();

    if (meetings.length === 0) {
      container.innerHTML = '<p class="empty-text">No meetings yet. Upload one above.</p>';
      return;
    }

    container.innerHTML = meetings.map(m => `
      <div class="meeting-item" onclick="openMeeting(${m.id})">
        <div>
          <div class="meeting-title">${m.title}</div>
          <div class="meeting-meta">${formatDate(m.created_at)}</div>
        </div>
        <div class="meeting-right">
          <span class="badge ${m.status}">${m.status}</span>
          <button class="btn-danger" onclick="confirmDelete(event, ${m.id}, '${m.title}')">Delete</button>
        </div>
      </div>
    `).join('');

  } catch (err) {
    container.innerHTML = '<p class="empty-text">Could not connect to server. Is Flask running?</p>';
  }
}

// ── DELETE MODAL ──
function confirmDelete(event, id, title) {
  event.stopPropagation();

  // Create modal overlay
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id        = 'deleteModal';
  overlay.innerHTML = `
    <div class="modal-box">
      <div class="modal-icon">🗑️</div>
      <div class="modal-title">Delete Meeting?</div>
      <div class="modal-message">
        Are you sure you want to delete<br>
        <strong>"${title}"</strong>?<br>
        This action cannot be undone.
      </div>
      <div class="modal-actions">
        <button class="btn-cancel" onclick="closeModal()">Cancel</button>
        <button class="btn-delete" onclick="deleteMeeting(${id})">Delete</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  // Close on overlay click
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeModal();
  });
}

function closeModal() {
  const modal = document.getElementById('deleteModal');
  if (modal) modal.remove();
}

async function deleteMeeting(id) {
  closeModal();
  await fetch(`${API}/meetings/${id}`, { method: 'DELETE' });
  loadMeetings();
}

// ── OPEN MEETING ──
function openMeeting(id) {
  window.location.href = `meeting.html?id=${id}`;
}

// ── HELPERS ──
function showStatus(msg, type) {
  const bar         = document.getElementById('uploadStatus');
  bar.style.display = 'block';
  bar.className     = `status-bar ${type}`;
  bar.textContent   = msg;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleString();
}

// Load on page start
loadMeetings();