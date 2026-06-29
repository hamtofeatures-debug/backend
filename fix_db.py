from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        # Add missing columns to payment table one by one
        try:
            conn.execute(text("ALTER TABLE payment ADD COLUMN user_id INTEGER REFERENCES user(id)"))
        except: pass
        try:
            conn.execute(text("ALTER TABLE payment ADD COLUMN amount FLOAT"))
        except: pass
        try:
            conn.execute(text("ALTER TABLE payment ADD COLUMN product_type VARCHAR(30)"))
        except: pass
        try:
            conn.execute(text("ALTER TABLE payment ADD COLUMN provider VARCHAR(20)"))
        except: pass
        try:
            conn.execute(text("ALTER TABLE payment ADD COLUMN reference VARCHAR(100)"))
        except: pass
        try:
            conn.execute(text("ALTER TABLE payment ADD COLUMN external_transaction_id VARCHAR(100)"))
        except: pass
        try:
            conn.execute(text("ALTER TABLE payment ADD COLUMN status VARCHAR(20) DEFAULT 'pending'"))
        except: pass
        try:
            conn.execute(text("ALTER TABLE payment ADD COLUMN created_at DATETIME"))
        except: pass
        try:
            conn.execute(text("ALTER TABLE payment ADD COLUMN expires_at DATETIME"))
        except: pass
        
        conn.commit()
        print("✅ Payment table updated successfully!")