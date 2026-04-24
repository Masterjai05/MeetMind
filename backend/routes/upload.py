import os
import threading
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from database import get_db
from services.transcriber import transcribe_audio
from services.summarizer import summarize_transcript

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'm4a', 'ogg', 'webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_meeting(meeting_id, filepath):
    """Runs transcription + summarization in background thread"""
    from app import app  # ✅ Fix 2 — import app for context
    with app.app_context():  # ✅ Fix 2 — push app context inside thread
        db = get_db()
        try:
            # Step 1 — Update status to transcribing
            db.execute("UPDATE meetings SET status = 'transcribing' WHERE id = ?", (meeting_id,))
            db.commit()

            # Step 2 — Transcribe audio
            print(f"[INFO] Transcribing meeting {meeting_id}...")
            transcript = transcribe_audio(filepath)

            # Step 3 — Save transcript
            db.execute("UPDATE meetings SET transcript = ?, status = 'summarizing' WHERE id = ?",
                       (transcript, meeting_id))
            db.commit()

            # Step 4 — Summarize + extract action items
            print(f"[INFO] Summarizing meeting {meeting_id}...")
            result = summarize_transcript(transcript)

            # Step 5 — Save everything, mark as done
            db.execute("""
                UPDATE meetings
                SET summary = ?, action_items = ?, decisions = ?, status = 'done'
                WHERE id = ?
            """, (result['summary'], result['action_items'], result['decisions'], meeting_id))
            db.commit()
            print(f"[INFO] Meeting {meeting_id} processed successfully.")

        except Exception as e:
            print(f"[ERROR] Meeting {meeting_id} failed: {e}")
            db.execute("UPDATE meetings SET status = 'failed' WHERE id = ?", (meeting_id,))
            db.commit()
        finally:
            db.close()


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'audio' not in request.files:
        return jsonify({'error': 'No file uploaded. Key must be "audio"'}), 400

    file = request.files['audio']
    title = request.form.get('title', 'Untitled Meeting')

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Use: {ALLOWED_EXTENSIONS}'}), 400

    # Save file securely
    filename = secure_filename(file.filename)
    filepath = os.path.join('uploads', filename)
    os.makedirs('uploads', exist_ok=True)
    file.save(filepath)

    # Create meeting record in DB
    db = get_db()
    cursor = db.execute(
        "INSERT INTO meetings (title, filename, status) VALUES (?, ?, 'uploaded')",
        (title, filename)
    )
    meeting_id = cursor.lastrowid
    db.commit()
    db.close()

    # Start background processing (transcription + summarization)
    thread = threading.Thread(target=process_meeting, args=(meeting_id, filepath))
    thread.daemon = True
    thread.start()

    return jsonify({
        'message': 'File uploaded successfully. Processing started.',
        'meeting_id': meeting_id,
        'title': title,
        'status': 'uploaded'
    }), 201