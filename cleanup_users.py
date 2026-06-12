"""
Run this once from the backend/ folder (with venv activated) to remove
demo/seed accounts, keeping only the user(s) listed in KEEP_EMAILS.

    python cleanup_users.py
"""

from app import app
from extensions import db
from models import User, Farmer, Expert, Business

KEEP_EMAILS = [
    "hamtofeatures@gmail.com",  # your real account - add others you want to keep
]

with app.app_context():
    users_to_delete = User.query.filter(~User.email.in_(KEEP_EMAILS)).all()

    for u in users_to_delete:
        print(f"Deleting {u.fullname} ({u.email}) - role: {u.role}")

        # Remove related role-specific rows first to avoid orphaned data
        Farmer.query.filter_by(user_id=u.id).delete()
        Expert.query.filter_by(user_id=u.id).delete()
        Business.query.filter_by(user_id=u.id).delete()

        db.session.delete(u)

    db.session.commit()
    print(f"Done. Deleted {len(users_to_delete)} user(s).")
    print("Remaining users:")
    for u in User.query.all():
        print(f"  - {u.fullname} ({u.email}) - {u.role}")