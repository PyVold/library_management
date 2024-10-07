import os

here = os.path.dirname(__file__)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + here + '/instance/library.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
