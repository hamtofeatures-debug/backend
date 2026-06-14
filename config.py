import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def get_database_uri():
    uri = os.environ.get('DATABASE_URL')
    if uri:
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        return uri
    return 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'agrosphere.db')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False