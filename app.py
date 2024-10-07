from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # Import Flask-Migrate
from config import Config
from models import db
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3
import os
#from werkzeug.middleware.proxy_fix import ProxyFix

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
#app.wsgi_app = ProxyFix(app.wsgi_app)


# Configuration for file uploads
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 MB limit

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In app.py
@app.context_processor
def inject_current_year():
    from datetime import datetime
    return {'current_year': datetime.utcnow().year}
# Initialize the database
db.init_app(app)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # For SQLite only
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
        
        
# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Register Blueprints (modular routes)
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.student import student_bp
from routes.teacher import teacher_bp

app.register_blueprint(teacher_bp)
app.register_blueprint(student_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)


# Create database tables if they don't exist
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='5001')


