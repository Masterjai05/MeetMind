from flask import Flask
from flask_cors import CORS
from database import init_db
from routes.upload import upload_bp
from routes.meetings import meetings_bp
from routes.chat import chat_bp

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Register blueprints (each file's routes)
app.register_blueprint(upload_bp)
app.register_blueprint(meetings_bp)
app.register_blueprint(chat_bp)

# Create database tables on startup
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)