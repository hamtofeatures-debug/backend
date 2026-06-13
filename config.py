import os
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///agrosphere.db')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me') or 'supersecretkey'

    # Explicit absolute path - avoids Flask resolving 'sqlite:///agrosphere.db'
    # to a different location (e.g. backend/instance/) depending on context.
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL')
        or 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'agrosphere.db')
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False