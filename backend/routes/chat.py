from flask import Blueprint, request, jsonify
from database import get_db
from services.rag import get_answer

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/meetings/<int:meeting_id>/chat', methods=['POST'])
def chat(meeting_id):
    """Accepts a question, returns an AI answer based on the transcript"""
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({'error': 'No question provided'}), 400

    question = data['question']

    # Get transcript for this meeting
    db = get_db()
    meeting = db.execute(
        "SELECT transcript, status FROM meetings WHERE id = ?", (meeting_id,)
    ).fetchone()

    if not meeting:
        return jsonify({'error': 'Meeting not found'}), 404

    if meeting['status'] != 'done':
        return jsonify({'error': 'Meeting is still being processed. Try again shortly.'}), 400

    if not meeting['transcript']:
        return jsonify({'error': 'No transcript found for this meeting'}), 400

    # Get previous chat history for context
    history = db.execute(
        "SELECT role, message FROM chat_messages WHERE meeting_id = ? ORDER BY created_at ASC",
        (meeting_id,)
    ).fetchall()
    chat_history = [dict(h) for h in history]

    # Get AI answer using RAG
    answer = get_answer(question, meeting['transcript'], chat_history)

    # Save user question + AI answer to DB
    db.execute(
        "INSERT INTO chat_messages (meeting_id, role, message) VALUES (?, 'user', ?)",
        (meeting_id, question)
    )
    db.execute(
        "INSERT INTO chat_messages (meeting_id, role, message) VALUES (?, 'assistant', ?)",
        (meeting_id, answer)
    )
    db.commit()
    db.close()

    return jsonify({
        'question': question,
        'answer': answer
    })


@chat_bp.route('/meetings/<int:meeting_id>/chat', methods=['GET'])
def get_chat_history(meeting_id):
    """Returns full chat history for a meeting"""
    db = get_db()
    messages = db.execute(
        "SELECT role, message, created_at FROM chat_messages WHERE meeting_id = ? ORDER BY created_at ASC",
        (meeting_id,)
    ).fetchall()
    db.close()

    return jsonify([dict(m) for m in messages])