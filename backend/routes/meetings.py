from flask import Blueprint, jsonify
from database import get_db

meetings_bp = Blueprint('meetings', __name__)

@meetings_bp.route('/meetings', methods=['GET'])
def get_meetings():
    """Returns all meetings"""
    db = get_db()
    meetings = db.execute(
        "SELECT id, title, status, created_at FROM meetings ORDER BY created_at DESC"
    ).fetchall()
    db.close()

    return jsonify([dict(m) for m in meetings])


@meetings_bp.route('/meetings/<int:meeting_id>', methods=['GET'])
def get_meeting(meeting_id):
    """Returns full details of one meeting"""
    db = get_db()
    meeting = db.execute(
        "SELECT * FROM meetings WHERE id = ?", (meeting_id,)
    ).fetchone()
    db.close()

    if not meeting:
        return jsonify({'error': 'Meeting not found'}), 404

    return jsonify(dict(meeting))


@meetings_bp.route('/meetings/<int:meeting_id>/status', methods=['GET'])
def get_status(meeting_id):
    """Polls processing status — frontend uses this to check when meeting is ready"""
    db = get_db()
    meeting = db.execute(
        "SELECT id, status FROM meetings WHERE id = ?", (meeting_id,)
    ).fetchone()
    db.close()

    if not meeting:
        return jsonify({'error': 'Meeting not found'}), 404

    return jsonify({'meeting_id': meeting_id, 'status': meeting['status']})


@meetings_bp.route('/meetings/<int:meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    """Deletes a meeting and its chat history"""
    db = get_db()
    db.execute("DELETE FROM chat_messages WHERE meeting_id = ?", (meeting_id,))
    db.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
    db.commit()
    db.close()

    return jsonify({'message': f'Meeting {meeting_id} deleted successfully'})