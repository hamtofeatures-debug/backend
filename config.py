import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def get_database_uri():
    # 1. Check for Render's PostgreSQL environment variable
    uri = os.environ.get('DATABASE_URL')
    
    if uri:
        # Render URLs use 'postgres://', but SQLAlchemy 1.4+ requires 'postgresql://'
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        return uri
    
    # 2. Local Fallback: Ensure the 'instance' directory exists so SQLite doesn't crash
    instance_dir = os.path.join(BASE_DIR, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    
    return 'sqlite:///' + os.path.join(instance_dir, 'agrosphere.db')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False