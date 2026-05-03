import os
import threading
import json
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from database import get_db
from services.transcriber import transcribe_audio
from services.summarizer import summarize_transcript

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'm4a', 'ogg', 'webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def replace_speaker_names(transcript: str, speaker_names: dict) -> str:
    """
    Replaces Speaker A, Speaker B etc. with actual names.
    speaker_names = {"A": "Priya", "B": "Arjun"}
    """
    for letter, name in speaker_names.items():
        transcript = transcript.replace(f"Speaker {letter}:", f"{name}:")
    return transcript


def process_meeting(meeting_id, filepath, speaker_names: dict):
    """Runs transcription + summarization in background thread"""
    from app import app
    with app.app_context():
        db = get_db()
        try:
            # Step 1 — Update status to transcribing
            db.execute("UPDATE meetings SET status = 'transcribing' WHERE id = ?", (meeting_id,))
            db.commit()

            # Step 2 — Transcribe audio
            print(f"[INFO] Transcribing meeting {meeting_id}...")
            transcript = transcribe_audio(filepath)

            # Step 3 — Replace speaker labels with names if provided
            if speaker_names:
                transcript = replace_speaker_names(transcript, speaker_names)
                print(f"[INFO] Speaker names applied: {speaker_names}")

            # Step 4 — Save transcript
            db.execute("UPDATE meetings SET transcript = ?, status = 'summarizing' WHERE id = ?",
                       (transcript, meeting_id))
            db.commit()

            # Step 5 — Summarize + extract action items
            print(f"[INFO] Summarizing meeting {meeting_id}...")
            result = summarize_transcript(transcript)

            # Step 6 — Save everything, mark as done
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

    file  = request.files['audio']
    title = request.form.get('title', 'Untitled Meeting')

    # Parse speaker names from form
    # Expected format: {"A": "Priya", "B": "Arjun", "C": "Ravi"}
    speaker_names_raw = request.form.get('speaker_names', '{}')
    try:
        speaker_names = json.loads(speaker_names_raw)
    except json.JSONDecodeError:
        speaker_names = {}

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

    # Start background processing
    thread = threading.Thread(target=process_meeting, args=(meeting_id, filepath, speaker_names))
    thread.daemon = True
    thread.start()

    return jsonify({
        'message': 'File uploaded successfully. Processing started.',
        'meeting_id': meeting_id,
        'title': title,
        'status': 'uploaded'
    }), 201