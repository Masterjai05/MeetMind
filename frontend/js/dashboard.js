const API = 'http://127.0.0.1:5000';

let selectedFile = null;

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

  const title = document.getElementById('meetingTitle').value.trim() || 'Untitled Meeting';
  const btn = document.getElementById('uploadBtn');
  btn.disabled = true;
  btn.textContent = 'Uploading...';

  const formData = new FormData();
  formData.append('audio', selectedFile);
  formData.append('title', title);

  try {
    showStatus('Uploading file...', 'info');

    const res = await fetch(`${API}/upload`, {
      method: 'POST',
      body: formData
    });

    const data = await res.json();

    if (!res.ok) {
      showStatus(`Error: ${data.error}`, 'error');
      return;
    }

    showStatus(`Uploaded! Processing started for "${data.title}". This may take a few minutes...`, 'info');

    // Poll status every 5 seconds
    pollStatus(data.meeting_id);

    // Refresh meetings list
    loadMeetings();

  } catch (err) {
    showStatus('Upload failed. Make sure the Flask server is running.', 'error');
    console.error(err);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Upload & Process';
  }
}

// ── POLL STATUS ──
async function pollStatus(meetingId) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`${API}/meetings/${meetingId}/status`);
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
    const res = await fetch(`${API}/meetings`);
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
          <button class="btn-danger" onclick="deleteMeeting(event, ${m.id})">Delete</button>
        </div>
      </div>
    `).join('');

  } catch (err) {
    container.innerHTML = '<p class="empty-text">Could not connect to server. Is Flask running?</p>';
  }
}

// ── OPEN MEETING ──
function openMeeting(id) {
  window.location.href = `meeting.html?id=${id}`;
}

// ── DELETE MEETING ──
async function deleteMeeting(event, id) {
  event.stopPropagation();
  if (!confirm('Delete this meeting?')) return;

  await fetch(`${API}/meetings/${id}`, { method: 'DELETE' });
  loadMeetings();
}

// ── HELPERS ──
function showStatus(msg, type) {
  const bar = document.getElementById('uploadStatus');
  bar.style.display = 'block';
  bar.className = `status-bar ${type}`;
  bar.textContent = msg;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleString();
}

// Load meetings on page load
loadMeetings();
